"""JevPersuader: fast, non-generative persuasion detection with calibrated evidence spans (v2).

One encoder pass produces three things:

  1. Label head (the "System One" decision): CLS -> 19 sigmoid probabilities p_t.
  2. Span proposer (the learned "parser", P1l): per-technique start and end scores on every
     token. A span [i, j) scores start_t(i) + end_t(j-1); the top-K spans per technique up to
     MAX_SPAN_LEN tokens are proposed. Cost is linear in paragraph length.
  3. Evidence scorer: each proposed span is pooled ([first token; last token; mean; width]) and
     scored q_{t,s} = P(span s is gold evidence for t), trained with a plain Brier score so q is
     a calibrated probability.

Every cited span is a token range of the input, so it is an exact substring: grounded by
construction. Two prediction modes come out of the same pass: full-text p_t (label head) and
span-grounded max_s q_{t,s} (the label implied by the best evidence span).

T0 control = the same class with evidence=False (same encoder, same label head, same data).

v1 -> v2 (2026-09-23): v1 scored every window of 1..12 tokens. 21% of gold spans are longer
than 12 tokens (Doubt median 19, Causal_Oversimplification 20), so they could never be cited.
v2 proposes spans up to 64 tokens (99.3% of gold) with the learned boundary proposer instead.
v1 also used a pos-weighted Brier, which moves the optimum above the true frequency and so
breaks calibration; v2 uses the unweighted (proper) Brier on the small proposal set.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoModel

BACKBONE = "microsoft/deberta-v3-base"
NUM_LABELS = 19
MAX_SPAN_LEN = 64  # covers 99.3% of train gold spans (DeBERTa tokens)
TOP_K = 8          # proposals per technique per paragraph
IOU_POS = 0.5      # a proposal counts as evidence when token IoU with a gold span >= 0.5


def load_backbone(name: str = BACKBONE) -> AutoModel:
    """DeBERTa-v3 ships fp16 weights; force fp32 (matches the RST paper's loader)."""
    try:
        return AutoModel.from_pretrained(name, use_safetensors=True, dtype=torch.float32)
    except TypeError:  # older transformers
        return AutoModel.from_pretrained(name, use_safetensors=True, torch_dtype=torch.float32)


def content_mask(attention_mask: torch.Tensor) -> torch.Tensor:
    """Real text tokens: attended, excluding [CLS] (position 0) and the final [SEP]."""
    m = attention_mask.bool().clone()
    m[:, 0] = False
    last = attention_mask.sum(1) - 1
    m[torch.arange(m.size(0), device=m.device), last] = False
    return m


def edu_runs(bounds: torch.Tensor, content: torch.Tensor, max_run: int = 3,
             max_len: int = MAX_SPAN_LEN):
    """Spans made of 1..max_run consecutive EDUs from per-token boundary indicators
    (B, L, 2) (start, end). Returns flat (b, i, j) with j exclusive."""
    bs, is_, js = [], [], []
    for b in range(bounds.size(0)):
        st = [int(k) for k in (bounds[b, :, 0] & content[b]).nonzero().squeeze(-1).tolist()]
        en = [int(k) for k in (bounds[b, :, 1] & content[b]).nonzero().squeeze(-1).tolist()]
        edus = []
        for k, s0 in enumerate(st):
            nxt = st[k + 1] if k + 1 < len(st) else 10 ** 9
            e = next((e for e in en if s0 <= e < nxt), None)
            if e is not None:
                edus.append((s0, e + 1))
        for k in range(len(edus)):
            for r in range(max_run):
                if k + r < len(edus) and edus[k + r][1] - edus[k][0] <= max_len:
                    bs.append(b); is_.append(edus[k][0]); js.append(edus[k + r][1])
    t = lambda x: torch.tensor(x, dtype=torch.long, device=bounds.device)  # noqa: E731
    return t(bs), t(is_), t(js)


class JevPersuader(nn.Module):
    def __init__(self, backbone: str = BACKBONE, num_labels: int = NUM_LABELS,
                 evidence: bool = True, max_span_len: int = MAX_SPAN_LEN, top_k: int = TOP_K,
                 width_dim: int = 32, span_hidden: int = 256, parser: str = "none") -> None:
        """parser: "none"; "multitask" (segmenter head trained, not coupled: control);
        "prior" (segmenter coupled to the proposer by per-technique gates, and its boundary
        probabilities given to the evidence scorer). See notes/parser_design.md."""
        super().__init__()
        assert parser in ("none", "multitask", "prior")
        self.encoder = load_backbone(backbone)
        H = self.encoder.config.hidden_size
        self.T = num_labels
        self.evidence = evidence
        self.parser = parser
        self.prior_mode = "pred"  # eval-time: pred | oracle | shift | zero
        self.struct_mode = "none"  # eval-time structural candidates: none | pred | oracle
        self.max_span_len = max_span_len
        self.top_k = top_k
        self.dropout = nn.Dropout(0.1)
        self.label_head = nn.Linear(H, num_labels)
        extra = 2 if parser == "prior" else 0
        if parser != "none":
            self.segmenter = nn.Linear(H, 2)  # P(EDU starts here), P(EDU ends here)
        if parser == "prior":
            self.gate = nn.Parameter(torch.zeros(2, num_labels))  # a_t (start), b_t (end)
        if evidence:
            self.boundary = nn.Linear(H, 2 * num_labels)
            self.width_emb = nn.Embedding(max_span_len + 1, width_dim)
            self.span_scorer = nn.Sequential(
                nn.Linear(3 * H + width_dim + extra, span_hidden), nn.GELU(), nn.Dropout(0.1),
                nn.Linear(span_hidden, num_labels))

    # ----------------------------------------------------------------------------- proposer
    @torch.no_grad()
    def propose(self, start: torch.Tensor, end: torch.Tensor, content: torch.Tensor):
        """Top-K spans per (paragraph, technique). Returns flat (b, t, i, j) with j exclusive."""
        B, L, T = start.shape
        W = min(self.max_span_len, L)
        s = start.float().masked_fill(~content.unsqueeze(-1), float("-inf"))
        e = end.float().masked_fill(~content.unsqueeze(-1), float("-inf"))
        e_pad = F.pad(e, (0, 0, 0, W - 1), value=float("-inf"))      # (B, L+W-1, T)
        e_win = e_pad.unfold(1, W, 1)                                # (B, L, T, W)
        scores = s.unsqueeze(-1) + e_win                             # span [i, i+w]
        scores = scores.permute(0, 2, 1, 3).reshape(B, T, L * W)
        k = min(self.top_k, L * W)
        top, idx = scores.topk(k, dim=-1)                            # (B, T, k)
        ok = torch.isfinite(top)
        b = torch.arange(B, device=start.device).view(B, 1, 1).expand(B, T, k)
        t = torch.arange(T, device=start.device).view(1, T, 1).expand(B, T, k)
        i = idx // W
        j = i + idx % W + 1
        return b[ok], t[ok], i[ok], j[ok]

    def score_spans(self, h, pb, pt, pi, pj, prior=None):
        cs = torch.cumsum(F.pad(h.float(), (0, 0, 1, 0)), dim=1)     # (B, L+1, H)
        width = (pj - pi).clamp(min=1)
        mean = (cs[pb, pj] - cs[pb, pi]) / width.unsqueeze(-1).float()
        parts = [h[pb, pi].float(), h[pb, pj - 1].float(), mean,
                 self.width_emb(width.clamp(max=self.max_span_len)).float()]
        if prior is not None:
            parts.append(torch.stack([prior[pb, pi, 0], prior[pb, pj - 1, 1]], dim=-1).float())
        rep = torch.cat(parts, dim=-1)
        rep = rep.to(h.dtype)
        logits = self.span_scorer(self.dropout(rep))                 # (N, T)
        return logits.gather(1, pt.unsqueeze(1)).squeeze(1)          # (N,)

    # ------------------------------------------------------------------------------ forward
    def edu_prior(self, seg_logits, content, seg_oracle=None):
        """Detached EDU boundary probabilities (B, L, 2) under the current prior_mode."""
        p = torch.sigmoid(seg_logits.detach().float())
        if self.prior_mode == "oracle" and seg_oracle is not None:
            p = seg_oracle.float()
        elif self.prior_mode == "zero":
            p = torch.zeros_like(p)
        elif self.prior_mode == "shift":
            # matched control: same boundary probabilities, moved by a random offset inside
            # each paragraph's content tokens (keeps count and shape, breaks position)
            out = torch.zeros_like(p)
            g = torch.Generator(device="cpu").manual_seed(12345)
            for b in range(p.size(0)):
                idx = content[b].nonzero().squeeze(-1)
                n = idx.numel()
                if n > 1:
                    k = int(torch.randint(1, n, (1,), generator=g))
                    out[b, idx] = p[b, idx].roll(k, dims=0)
            p = out
        return p * content.unsqueeze(-1).float()

    def forward(self, input_ids, attention_mask, gold=None, seg_oracle=None):
        """gold: (B, S, 3) long (technique, i, j) padded with -1, added to the proposals during
        training so the scorer always sees positives. Leave None at inference.
        seg_oracle: (B, L, 2) silver EDU boundaries, used only when prior_mode == "oracle"."""
        h = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        out = {"label_logits": self.label_head(self.dropout(h[:, 0, :]))}
        content = content_mask(attention_mask)
        prior = None
        if self.parser != "none":
            out["seg_logits"] = self.segmenter(self.dropout(h))
            if self.parser == "prior":
                prior = self.edu_prior(out["seg_logits"], content, seg_oracle)
        if not self.evidence:
            return out
        B, L, _ = h.shape
        bl = self.boundary(self.dropout(h))
        start, end = bl[..., :self.T], bl[..., self.T:]
        if prior is not None:
            start = start + prior[..., 0:1] * self.gate[0]
            end = end + prior[..., 1:2] * self.gate[1]
        pb, pt, pi, pj = self.propose(start.detach(), end.detach(), content)
        if self.struct_mode != "none" and gold is None:
            if self.struct_mode == "oracle" and seg_oracle is not None:
                bnd = seg_oracle > 0.5
            elif self.struct_mode == "pred" and "seg_logits" in out:
                bnd = torch.sigmoid(out["seg_logits"].float()) >= 0.5
            else:
                bnd = None
            if bnd is not None:
                eb, ei, ej = edu_runs(bnd, content)
                n = eb.numel()
                if n:
                    tt = torch.arange(self.T, device=h.device)
                    pb = torch.cat([pb, eb.repeat_interleave(self.T)])
                    pt = torch.cat([pt, tt.repeat(n)])
                    pi = torch.cat([pi, ei.repeat_interleave(self.T)])
                    pj = torch.cat([pj, ej.repeat_interleave(self.T)])
        if gold is not None:
            g = gold.view(-1, 3)
            gb = torch.arange(B, device=h.device).repeat_interleave(gold.size(1))
            keep = g[:, 0] >= 0
            pb = torch.cat([pb, gb[keep]])
            pt = torch.cat([pt, g[keep, 0]])
            pi = torch.cat([pi, g[keep, 1]])
            pj = torch.cat([pj, g[keep, 2]])
        q_logit = self.score_spans(h, pb, pt, pi, pj, prior)
        q = torch.sigmoid(q_logit.float())
        qmax = torch.zeros(B * self.T, device=h.device, dtype=q.dtype)
        qmax = qmax.scatter_reduce(0, pb * self.T + pt, q, reduce="amax", include_self=True)
        out.update(start_logits=start, end_logits=end, content=content, pb=pb, pt=pt, pi=pi,
                   pj=pj, q_logit=q_logit, q=q, qmax=qmax.view(B, self.T))
        return out


# ---------------------------------------------------------------------------------- losses
def proposal_targets(gold: torch.Tensor, pb, pt, pi, pj, iou_pos: float = IOU_POS):
    """1 when the proposal overlaps a gold span of the same technique with token IoU >= iou_pos."""
    g = gold[pb]                                                     # (N, S, 3)
    same = (g[..., 0] == pt.unsqueeze(1)) & (g[..., 0] >= 0)
    inter = (torch.minimum(pj.unsqueeze(1), g[..., 2])
             - torch.maximum(pi.unsqueeze(1), g[..., 1])).clamp(min=0)
    union = (pj - pi).unsqueeze(1) + (g[..., 2] - g[..., 1]) - inter
    iou = torch.where(same, inter.float() / union.clamp(min=1).float(), torch.zeros_like(inter,
                      dtype=torch.float))
    return (iou.max(dim=1).values >= iou_pos).float()


def losses(out: dict, batch: dict, alpha: float = 1.0, beta: float = 0.1, gamma: float = 1.0,
           boundary_pos_weight: float = 20.0, seg_weight: float = 1.0):
    """CEA objective.

    L = BCE(labels)                                       every view
      + gamma * BCE(start/end boundaries)                 proposer, evidence-known slots
      + alpha * Brier(q, proposal is gold evidence)       evidence-known slots (proper score)
      + beta  * (p_t - max_s q_{t,s})^2                   every view (label-evidence consistency)

    Evidence-known slots: views with evidence_present, techniques whose location is known (label 0,
    or at least one gold span located). The Brier is summed over each slot's proposals and averaged
    over slots, so every proposal has equal weight (keeps it a proper score).
    """
    y = batch["label"]
    logits = out["label_logits"].float()
    l_label = F.binary_cross_entropy_with_logits(logits, y)
    comp = {"label": float(l_label)}
    base = l_label
    if "seg_logits" in out and batch.get("seg_mask") is not None and batch["seg_mask"].any():
        # distillation of the DMRST segmentation (silver EDU starts/ends) into the segmenter
        m = batch["seg_mask"].unsqueeze(-1).float().expand(-1, -1, 2)
        ce = F.binary_cross_entropy_with_logits(out["seg_logits"].float(), batch["seg"],
                                                reduction="none")
        l_seg = (ce * m).sum() / m.sum()
        base = base + seg_weight * l_seg
        comp["segment"] = float(l_seg)
    if "q" not in out:
        return base, comp
    B, T = y.shape
    slot = batch["ev"].unsqueeze(1) & batch["known"]                  # (B, T)
    gold = batch["gold"]
    # proposer targets
    L = out["start_logits"].size(1)
    st = torch.zeros(B, L, T, device=y.device)
    en = torch.zeros(B, L, T, device=y.device)
    g = gold.view(-1, 3)
    gb = torch.arange(B, device=y.device).repeat_interleave(gold.size(1))
    keep = g[:, 0] >= 0
    st[gb[keep], g[keep, 1], g[keep, 0]] = 1.0
    en[gb[keep], (g[keep, 2] - 1).clamp(max=L - 1), g[keep, 0]] = 1.0
    bmask = (out["content"].unsqueeze(-1) & slot.unsqueeze(1)).float()
    pw = torch.tensor(boundary_pos_weight, device=y.device)
    l_b = torch.zeros((), device=y.device)
    if bmask.sum() > 0:
        for lg, tg in ((out["start_logits"], st), (out["end_logits"], en)):
            ce = F.binary_cross_entropy_with_logits(lg.float(), tg, pos_weight=pw,
                                                    reduction="none")
            l_b = l_b + (ce * bmask).sum() / bmask.sum()
    # evidence Brier on proposals
    pb, pt = out["pb"], out["pt"]
    tgt = proposal_targets(gold, pb, pt, out["pi"], out["pj"])
    pmask = slot[pb, pt].float()
    n_slots = slot.sum().clamp(min=1).float()
    l_evd = (((out["q"] - tgt) ** 2) * pmask).sum() / n_slots
    # consistency on every view
    p = torch.sigmoid(logits)
    l_cons = ((p - out["qmax"]) ** 2).mean()
    loss = base + gamma * l_b + alpha * l_evd + beta * l_cons
    comp.update(boundary=float(l_b), evidence=float(l_evd), consistency=float(l_cons),
                ev_pos=float((tgt * pmask).sum()), ev_n=float(pmask.sum()))
    return loss, comp
