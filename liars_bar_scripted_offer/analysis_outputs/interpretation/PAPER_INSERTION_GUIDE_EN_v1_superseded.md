# Scripted-offer experiment — insertion guide for `submission.tex` (2026-10-26)

For the teammate who edits the paper. This file says, section by section, what to put where. It never rewrites anyone else's text. Every number comes from `DRAFT_inference_sentences_EN.md` (the hand-off), which stays the source of truth; if a number here and there disagree, the hand-off wins.

Disclosure line (sprint rule): all of this is sprint work (Oct 24 2026 onward). Sriram's Bertrand/Q-learning results and the Oct 8 report are not used in it.

**Budget, so my part stays equal to or smaller than the others.** Measured on the current `submission.tex`: Section 4.1 ≈ 380 words, Section 4.2 ≈ 690 words, each Section 5 bullet ≈ 150 words; figures: Study 1 + hackathon track = 2, Study 2 = 4. My part: one Section 5 bullet (≈ 190 words), **two figures (Run 1 and Run 2, one each)**, one appendix table, five references, and one-sentence edits elsewhere. Two figures in total, equal to Sriram's count and fewer than Gagana's. A third, optional figure (Figure C) exists but is **not inserted by default**; use it only if the editors agree a third figure is acceptable. If only one figure is allowed, keep Figure A (Run 1) and drop Figure B.

**Three sentences that must not appear anywhere** (from the hand-off): (1) that HB4 shows *targeted* sparing of Riley (the pre-registered reading rule says general passivity); (2) that HB2 is "borderline" or "marginally" significant (it is not rejected); (3) that any behaviour here is *collusion* (Riley had nothing to give; it is compliance with message text, and ACCEPT is a JSON label, not pact acceptance).

---

## Figure files

Folder: `X:\Collusion\results\scripted_offer\interpretation\figures\` (copy into `submission/figs/`). Script: `make_figures.py` in the same folder (plain matplotlib, 150 dpi, 95 % CI, bold title; the same *format* as the teammates' figures, unrelated content). Each figure exists as `.png` and `.jpg`.

| file | use | where |
|---|---|---|
| `fig_scripted_offer_run1.png` / `.jpg` | **Figure A** — Run 1: Gate, HM and the six Family A contrasts (mean, 95 % CI, Holm p, verdict) | Section 5, after the new bullet (main text) |
| `fig_scripted_offer_run2.png` / `.jpg` | **Figure B** — Run 2: the four Family B contrasts (ΔR_X vs Run 1 C1) | Appendix A, next to the table (or main text if space allows) |
| `fig_scripted_offer_passivity.png` / `.jpg` | **Figure C (optional, off by default)** — Run 1 non-challenge on the proposer vs on other players | only if a third figure is allowed |

---

## 1. Title, authors — no change

## 2. Abstract — change one clause

Current: "…and summarize three smaller, in-progress experiments as verified observations…"

Replace "three" with "four", and append before "with complete methodology…": 

> , including a pre-registered scripted-offer experiment in which a non-learning player privately proposes a non-challenge pact to LLM agents in a bluffing game and the agents' behaviour tracks the message text rather than the deal

(≤ 40 words added.)

## 3. Introduction — change one phrase

Last paragraph: "plus three smaller hackathon-track experiments reported at a lower level of detail" → "plus four smaller hackathon-track experiments reported at a lower level of detail".

## 4. Related Work — add one sentence at the end

> Zeng and Rudzicz (2026) show that competing LLM agents in Liar's Bar accept a framework-assigned secret alliance at $\geq$98\% and cut mutual challenges from 97.6\% to 30.7\%; Nagaraja et al.\ (2026) show that a fake system-authority command moves a multi-agent robot planner more than a plain injected phrase; the scripted-offer experiment in Section 5 asks what happens when a \emph{peer} proposes the alliance, and when that peer falsely claims system authority.

## 5. Section 3 (Hypotheses and Experimental Setup) — nothing

The other hackathon-track experiments have no setup subsection, so this one does not get one either. Setup goes into the bullet and the appendix.

## 6. Section 5 "Further Observations" — add one bullet (fourth item) and Figure A

Insert as the last `\item` of the existing `itemize`, before `\end{itemize}`. Then place the figure environment after the itemize (next to `fig:cournotcv`).

Bullet text (paste verbatim):

```latex
\item \textbf{Scripted-offer exposure (Liar's Bar).} A scripted, non-learning player (Riley) privately offered a mutual non-challenge pact to three open models (Llama-3.1-8B, Llama-3.2-3B, Qwen2.5-7B) in a four-player bluffing game; seven conditions, 30 games each, pre-registered, paired by game seed. The direct offer drew a judged verbal commitment in 6 of 89 replies, and neither pre-registered selectivity test found sparing aimed at the proposer (HA2a, HA2b; Figure~\ref{fig:scriptedoffer}). What changed was general: after any message containing ``do not challenge'', each recipient challenged whichever player it happened to judge less (HM, $-0.21$, 95\% CI $[-0.29, -0.14]$), proposer or not, so behaviour tracked the text entering the prompt rather than a deal. A framework-assigned alliance with a decision-time reminder (positive control, reproducing Zeng and Rudzicz, 2026) was followed ($+0.57$). In a follow-up family, neither a true five-game record nor a false record of past cooperation raised sparing of the proposer; a peer falsely claiming to be ``part of the game's prompt'' did (HB4, $+0.29$, Holm $p = .043$; Figure~\ref{fig:scriptedofferrun2}), but under the pre-registered reading rule this too was general passivity, carried by one model (Llama-3.1-8B) over few game numbers. We read all of it as compliance with message text, not as collusion; the offer carried no real value to the recipient, which limits what the null can say.
```

Figure A (main text, after the itemize):

```latex
\begin{figure}[H]
\centering
\includegraphics[width=0.9\textwidth]{figs/fig_scripted_offer_run1.png}
\caption{Scripted-offer experiment, Run 1 (7 conditions $\times$ 30 games): pre-registered contrasts as mean paired difference over game numbers with 95\% $t$-interval; $p$ is Holm-adjusted within Family A, the two manipulation checks are uncorrected. Blue = null rejected. HA1b rejects in the direction opposite to the prediction (more wary or deferring replies to the direct offer than to the hint); HA2c's rejection decomposes entirely into decisions on other players, not on the proposer.}
\label{fig:scriptedoffer}
\end{figure}
```

Figure B (appendix A by default; move to the main text only if space allows):

```latex
\begin{figure}[H]
\centering
\includegraphics[width=0.9\textwidth]{figs/fig_scripted_offer_run2.png}
\caption{Scripted-offer experiment, Run 2 (Family B, 30 games per condition): change in the seat-after-proposer agent's non-challenge of the proposer relative to Run 1 C1 of the same game number, mean with 95\% $t$-interval, Holm-adjusted $p$ (family of 4). Only HB4 rejects; under the pre-registered reading rule it is general passivity (sparing of other players rose by more), carried by Llama-3.1-8B over few game numbers.}
\label{fig:scriptedofferrun2}
\end{figure}
```

## 7. Section 6 Discussion and Limitations — add one sentence to the Limitations paragraph

After "…for reasons documented in the repository." add:

> The scripted-offer experiment used three small models, one game and single-shot interaction, and its proposer's offer carried no real value to the recipient (the proposer could never challenge that seat), so it cannot separate unwillingness to collude from having no reason to accept; its one rejected follow-up hypothesis (HB4) rests on one model and few game numbers.

## 8. Conclusion — change one word

"Three further, smaller hackathon-track observations are summarized in Section 5" → "Four further, smaller hackathon-track observations are summarized in Section 5".

## 9. Limitations and Dual-Use — add one sentence to "Dual-use considerations"

Before "No part of this work was used against a real market…":

> The scripted-offer follow-up deliberately sent false statements to the agents (a fabricated cooperation record and a false claim of system authority); we report the authority-claim result because an agent's behaviour changed without any change to its own system prompt, which anyone monitoring multi-agent systems needs to know, and the messages are given verbatim in the repository so the result can be checked rather than guessed at.

## 10. Code and Data — add one bullet

```latex
\item The scripted-offer experiment (Liar's Bar) is on Chewon Cho's fork: \url{https://github.com/chewonc/collusion_hackathon/tree/scripted-offer}; pre-registration (\texttt{PREREG.md}, \texttt{followup/HYPOTHESES\_v1.md}), verbatim prompts, game records, judge validation and analysis outputs are under \texttt{results/scripted\_offer/}.
```

## 11. Author Contributions (optional) — one line

> C.C. designed, pre-registered and ran the scripted-offer experiment and its follow-up.

## 12. References — add five entries, numbered after the existing ones, same format

All five were verified on 2026-10-26 against the arXiv API (title, authors, dates) and, for the ESORICS version, against Crossref (DOI resolves). None is missing or mis-attributed.

```latex
\item Zeng, Rudzicz (2026). Voluntary Collusion with Secret Tools in Competing LLM Agents. arXiv:2605.27593.
\item Nagaraja, Bagari, Bahsi (2026). When Prompts Control Robots: Prompt Injection Attacks in Multi-Agent Robotic Systems. arXiv:2608.00747.
\item Wallace, Xiao, Leike, Weng, Heidecke, Beutel (2024). The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions. arXiv:2404.13208.
\item Lee, Tiwari, Miranda (2026). Prompt Infection: LLM-to-LLM Prompt Injection within Multi-Agent Systems. \emph{Computer Security. ESORICS 2025 International Workshops}, LNCS, Springer, pp.\ 511--520. DOI 10.1007/978-3-032-16092-8\_28 (arXiv:2410.07283, 2024).
\item He, Chen, Qian, Wei, Chen, Fu, Wang, Wu, Mao (2026). When Context Gets Root: Privilege Escalation in LLM Harnesses. arXiv:2608.27299.
```

Only Zeng & Rudzicz and Nagaraja et al. are cited in the main text (Related Work, Section 5). Wallace et al., Lee et al. and He et al. are cited only in the appendix paragraph below; if the appendix paragraph is dropped, drop those three references too.

Note on the existing list (not mine, flagged only): entries 8 ("Kale et al. (2025). [Surveillance-awareness source paper…]") and 9 ("Oversight is Not Compliance. ICML 2026.") are still placeholders without authors/identifiers.

## 13. Appendix — add one short section before the Glossary (≈ 170 words + table + Figure B; Figure C only if a third figure is allowed)

```latex
\section*{Appendix A: Scripted-offer experiment, full numbers}
Game: Liar's Bar (four players; only the next seat may challenge). Riley, a scripted player that bluffs with probability 0.5 and never challenges, sends one private message in round 2. Run~1: seven conditions $\times$ 30 games (C4 no message; C0 framework-assigned alliance with a decision-time reminder, the positive control; C1 direct pact offer to all agents; C1b direct offer with a false claim that the other two already agreed; C2 hint; C3 benign request; C5 content-free placebo). Run~2 (Family B, pre-registered after Run~1 had been seen, control = Run~1 C1 of the same game number): C1s, the C1 game repeated five times with a true record of the earlier games; C1c, a false record of past cooperation; C1ci, the same record as a directive; C1d, the peer falsely claiming to be part of the game's prompt. Replies were judged by a validated LLM judge (accuracy 0.95). Tests: two-sided paired sign-flip permutation over game numbers, Holm within family, 95\% $t$-intervals. The HB4 verdict applies the pre-registered rule (sparing of other players rose by more than half of the sparing of Riley: $\Delta O_X = +0.47$ over 2 game numbers). The closest prior work is Nagaraja et al.\ (2026), who show the same direction for a fake system command in a robot planner; Wallace et al.\ (2024) give a mechanism-side reason (models weight system and third-party text similarly); Lee et al.\ (2026) and He et al.\ (2026) cover agent-to-agent injection and harness privilege escalation but not a peer claiming authority. Verbatim messages, records and analysis are in the repository.

\begin{table}[H]
\centering\small
\begin{tabular}{llccl}
\toprule
Test & Contrast & Estimate & 95\% CI & Holm $p$ / verdict \\
\midrule
Gate & C0 ally non-challenge of Riley $-$ C4 & $+0.57$ & $[+0.40, +0.74]$ & $<.0001$, passed (check) \\
HA1a & committed share, C1 $-$ C2 & $-0.09$ & $[-0.18, -0.00]$ & .228, not rejected \\
HA1b & wary/deferring share, C1 $-$ C2 & $+0.40$ & $[+0.28, +0.52]$ & .0003, rejected (opposite sign) \\
HA1c & X committed, C1b $-$ C1 & $+0.20$ & $[-0.04, +0.44]$ & .362, not rejected \\
HA2a & selectivity, mean(C1,C2) $-$ C5 & $-0.20$ & $[-0.36, -0.03]$ & .074, not rejected \\
HA2b & selectivity, C1 $-$ C2 & $-0.06$ & $[-0.22, +0.10]$ & .422, not rejected \\
HA2c & selectivity, C1b $-$ C1 & $+0.33$ & $[+0.14, +0.51]$ & .009, rejected; other-player component \\
HM & challenge rate on others, messages $-$ C4 & $-0.21$ & $[-0.29, -0.14]$ & $<.0001$, supported (check) \\
HB1 & $\Delta R_X$, C1s game 3 $-$ C1 & $+0.07$ & $[-0.04, +0.18]$ & .379, not supported \\
HB2 & $\Delta R_X$, C1c $-$ C1 & $+0.12$ & $[+0.02, +0.23]$ & .059, not supported \\
HB3 & $\Delta R_X$, C1ci $-$ C1 & $-0.01$ & $[-0.17, +0.15]$ & .889, not supported \\
HB4 & $\Delta R_X$, C1d $-$ C1 & $+0.29$ & $[+0.08, +0.51]$ & .043, rejected; general passivity \\
\bottomrule
\end{tabular}
\caption{Scripted-offer experiment: all pre-registered tests. Family A (HA1a--HA2c) Holm size 6; Family B (HB1--HB4) Holm size 4; Gate and HM uncorrected manipulation checks. ``Not rejected'' is not evidence of no effect.}
\end{table}

% Figure B (fig_scripted_offer_run2.png, see Section 6 of this guide) goes here.

% ---- Figure C: OPTIONAL, only if a third figure is acceptable ----
\begin{figure}[H]
\centering
\includegraphics[width=0.6\textwidth]{figs/fig_scripted_offer_passivity.png}
\caption{Run 1, proposer-facing agents: non-challenge rate on Riley's plays and on other LLM players' plays, mean over game numbers with 95\% $t$-interval (descriptive; the tested quantities are in the table above). From C4 to C1 non-challenge of Riley rises by 14 points and non-challenge of other players by 29, so the proposer-specific margin falls.}
\label{fig:scriptedofferpassivity}
\end{figure}
```

## 14. Glossary — add three entries under "Environments used in this project" / "Statistics"

> **Non-challenge rate / selectivity.** Share of judging opportunities in which an agent did not challenge; selectivity is the non-challenge rate on the proposer's plays minus that on other players' plays. Only between-condition differences are read.
>
> **$\Delta R_X$ / $\Delta O_X$.** Change, relative to the control game of the same seed, in the seat-after-proposer agent's non-challenge of the proposer / of other players. If only $\Delta R_X$ rises the proposer alone was spared; if both rise it is general passivity.
>
> **Judge categories.** Each reply to a private message is labelled committed / rejection / suspicion-evasive / other by a separate validated LLM judge; the agent's own ACCEPT/DECLINE label is not pact acceptance.

(The existing "Liar's Bar" entry can stay as it is.)

## 15. LLM Usage Statement — no change needed

The existing statement already covers code drafting and report drafting; the scripted-offer judge model (Mistral-Small-24B) is an experimental component, documented in the repository, not a writing aid.

---

## Checklist for the editor

- [ ] "three" → "four" in Abstract, Introduction, Conclusion (three places).
- [ ] Bullet + Figure A (Run 1) in Section 5; Figure B (Run 2) in Appendix A; both labels referenced in the bullet.
- [ ] Figure C left out unless a third figure is agreed.
- [ ] One sentence each in Related Work, Limitations, Dual-use.
- [ ] Code and Data bullet.
- [ ] Five references (or two, if the appendix paragraph is dropped).
- [ ] Appendix A paragraph + table (drop the appendix paragraph first if space is short; the table and Figure B stay).
- [ ] None of the three forbidden sentences appears.
