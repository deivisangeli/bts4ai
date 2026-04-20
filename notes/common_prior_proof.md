# Is the Common Prior Necessary for BTS? — A Detailed Proof

## 1. Setup

There are m possible answers, indexed k = 1,...,m. The unknown population distribution is θ = (θ_1,...,θ_m) ∈ Δ^m (the simplex). Each respondent r draws a true opinion t_r ∈ {1,...,m} and reports an answer x_r ∈ {1,...,m} and a predicted frequency vector y_r = (y_1^r,...,y_m^r) ∈ Δ^m.

In the infinite-population limit, the empirical endorsement frequency of answer k is:

    x_k = lim_{n→∞} (1/n) Σ_r 1[x_r = k]

and the geometric mean of predictions for answer k is:

    log ȳ_k = lim_{n→∞} (1/n) Σ_r log y_k^r

**BTS information score** for respondent r who reports answer j:

    IS(j) = log(x_j / ȳ_j)

**BTS total score** (Prelec's Eq. 2):

    Score_r = IS(x_r) + α · Σ_k x_k log(y_k^r / x_k)

The second term is a prediction accuracy bonus: it equals −α·D_KL(x || y^r), maximized (at 0) when y^r = x. Since the two parts are additively separable, we can analyze them independently.

---

## 2. The Formal Assumptions

Prelec's theorem rests on two structural conditions plus one regularity condition:

**Assumption 1 (Large population):** The number of respondents is large enough that one respondent's answer does not appreciably affect empirical frequencies. The proof is stated for n → ∞.

**Assumption 2 (Common prior + exchangeability):** There exists a distribution p(θ) over Δ^m such that respondents' opinions are i.i.d. given θ:

    P(t_1 = k_1, ..., t_n = k_n | θ) = Π_r θ_{k_r}

Equivalently (by de Finetti's representation theorem): opinions are *exchangeable* — the joint distribution is invariant under permutations of respondents.

**Assumption 3 (Stochastic relevance / impersonally informative):** Different true opinions imply different posteriors over θ:

    p(θ | t_r = i) ≠ p(θ | t_r = j)  whenever  i ≠ j

And the same true opinion always implies the same posterior:

    p(θ | t_r) depends only on t_r, not on r

This second part is what Prelec calls the "impersonally informative" condition.

**Truth-telling** is defined as: x_r = t_r and y_k^r = E[θ_k | t_r] for all k.

---

## 3. The Theorem

**T1 (Nash equilibrium):** Under Assumptions 1–3, if all other respondents report truthfully, then reporting truthfully maximizes expected information score for every respondent, for any α > 0.

**T2 (Pareto optimality):** The truth-telling equilibrium yields (weakly) higher expected scores for all respondents than any other equilibrium.

**T3 (Zero-sum):** With α = 1, the game is zero-sum and scores rank respondents by their accuracy about the true distribution.

---

## 4. Full Proof of T1

Fix a respondent with true opinion t_i = i. Suppose all others are truthful.

**Step 1: What the scoring looks like with truthful others.**

In the infinite-population limit, with everyone else truthful:
- x_k = θ_k (empirical frequency = true population share)
- Type-k respondents (fraction θ_k of the population) predict E[θ_j | t_k] for answer j
- Geometric mean: log ȳ_j = Σ_k θ_k · log E[θ_j | t_k]

So the information score for reporting answer j is:

    IS(j | θ) = log θ_j − Σ_k θ_k log E[θ_j | t_k]

**Step 2: Expected information score (step a in Prelec's footnote 23).**

The respondent doesn't observe θ; they condition on their own opinion t_i = i:

    E_i[IS(j)] = ∫_Θ p(θ | t_i = i) · IS(j | θ) dθ               ...(a)

    = ∫_Θ p(θ | t_i) [log θ_j − Σ_k θ_k log E[θ_j | t_k]] dθ      ...(b)

**Step 3: Apply conditional independence (deriving step c).**

This is the step where the common prior assumption does real work. Because opinions are i.i.d. given θ (Assumption 2), a fresh draw t_k is independent of t_i conditional on θ:

    P(t_k = k | θ, t_i) = P(t_k = k | θ) = θ_k

This lets us apply Bayes' rule to substitute:

    θ_k · p(θ | t_i) = P(t_k | θ) · p(θ | t_i) = p(t_k | t_i) · p(θ | t_k, t_i)

where the last equality is Bayes: p(θ | t_k, t_i) = θ_k · p(θ | t_i) / p(t_k | t_i).

Now E[θ_j | t_k] = ∫ θ_j p(θ | t_k) dθ is a constant (it doesn't depend on θ in the integral), so:

    ∫_Θ p(θ | t_i) θ_k log E[θ_j | t_k] dθ
    = p(t_k | t_i) · log E[θ_j | t_k] · ∫_Θ p(θ | t_k, t_i) dθ
    = p(t_k | t_i) · log E[θ_j | t_k]

Summing over k, the second part of (b) becomes:

    Σ_k p(t_k | t_i) · log E[θ_j | t_k]                            ...(c-part-2)

For the first part of (b), by the same conditional independence trick:

    ∫_Θ p(θ | t_i) log θ_j dθ = Σ_k p(t_k | t_i) ∫_Θ p(θ | t_k, t_i) log θ_j dθ

Now note that log θ_j = log E[θ_j | θ] (trivially, since θ is known), and by Bayes' rule applied to a further draw: p(t_j | θ, t_k, t_i) = θ_j (conditional independence again), so ∫_Θ p(θ|t_k,t_i) log θ_j dθ = E[log θ_j | t_k, t_i]. We can write this more usefully.

Pulling everything together, step (c) gives:

    E_i[IS(j)] = Σ_k p(t_k | t_i) [ E[log θ_j | t_k, t_i] − log E[θ_j | t_k] ]   ...(c)

**Step 4: Bayes' rule and the KL structure (deriving step d).**

Using Bayes' rule:

    p(θ | t_k, t_i) / p(θ | t_k) = p(t_i | θ, t_k) · p(θ | t_k) / [p(t_i | t_k) · p(θ | t_k)]
                                   = θ_i / p(t_i | t_k)

So:

    log p(θ | t_k, t_i) = log p(θ | t_k) + log θ_i − log p(t_i | t_k)

Substituting into the expression for E_i[IS(j)]:

    E[log θ_j | t_k, t_i] − log E[θ_j | t_k]

This is not yet KL form. The key move is to recognize that log E[θ_j | t_k] = log p(t_j | t_k) (i.e., the truthful prediction of a type-k respondent for answer j equals E[θ_j | t_k], which is the marginal probability that a random draw from the population gives answer j, conditioned on knowing one's own opinion is k).

So:

    E_i[IS(j)] = Σ_k p(t_k | t_i) ∫_Θ p(θ | t_k, t_i) log [p(θ | t_k, t_j) / p(θ | t_k)] dθ  ...(d)

The derivation of (d) from (c) uses Bayes applied to t_j: p(t_j | θ, t_k) = θ_j and p(θ | t_k, t_j) ∝ θ_j p(θ | t_k), so log θ_j = log p(θ | t_k, t_j) − log p(θ | t_k) + const, where the constant is log p(t_j | t_k). After substitution, the log p(t_j | t_k) term exactly cancels log E[θ_j | t_k], yielding (d).

**Step 5: The maximization argument.**

Expression (d) is:

    E_i[IS(j)] = Σ_k p(t_k | t_i) ∫_Θ p(θ | t_k, t_i) log p(θ | t_k, t_j) dθ  +  C_k

where C_k collects terms that don't depend on j.

By **Gibbs' inequality** (a.k.a. the entropy maximization principle):

    ∫ p(θ | t_k, t_i) log p(θ | t_k, t_j) dθ  ≤  ∫ p(θ | t_k, t_i) log p(θ | t_k, t_i) dθ

with equality if and only if p(θ | t_k, t_j) = p(θ | t_k, t_i) a.s.

By **Assumption 3 (stochastic relevance)**, p(θ | t_k, t_j) = p(θ | t_k, t_i) iff j = i.

Therefore: **E_i[IS(j)] < E_i[IS(i)] for all j ≠ i.** Truth-telling strictly maximizes expected information score. □

---

## 5. Which Assumptions Are Truly Necessary?

### The common prior: necessary or sufficient?

The common prior p(θ) plays three roles in the proof:

| Role | Where used | What it gives |
|---|---|---|
| (i) Conditional independence | Step 3 | Allows substitution θ_k p(θ\|t_i) = p(t_k\|t_i)p(θ\|t_k,t_i) |
| (ii) Impersonally informative | Step 1 | Makes E[θ_j\|t_k] well-defined (same for all type-k respondents) |
| (iii) Existence of p(θ\|t_k,t_j) | Step 4–5 | Enables Gibbs' inequality application |

**De Finetti's theorem** is the bridge: exchangeability of opinions ↔ existence of a common prior p(θ) such that opinions are i.i.d. given θ. The common prior is not an *additional* assumption — it is the *representation* of the more primitive assumption of exchangeability.

**Formally**: The common prior is necessary in the following sense: if opinions are not exchangeable (no common prior exists), then:
- The impersonally informative condition can fail: two respondents with the same opinion may form different posteriors (because they have different personal priors p_r(θ))
- The conditional independence substitution in Step 3 fails
- The proof breaks down

However, the common prior need not be *known* or *specified*. The scoring rule (Eq. 2) uses no knowledge of p(θ). This is the key practical advantage of BTS: the *existence* of a common prior is the theoretical requirement, but the *form* of that prior is irrelevant.

### What is truly necessary (minimal conditions):

1. **Exchangeability** (equivalently: existence of common prior p(θ)): Opinions are i.i.d. conditional on θ. This is the core structural requirement.

2. **Stochastic relevance**: Different opinions ↔ different posteriors p(θ|t). Without this, truth-telling is weakly but not strictly dominant (information score is the same for all answers with the same posterior).

3. **Large population**: So that no single respondent can move x_k appreciably, and so the law of large numbers applies.

That is all. The specific functional form of p(θ), whether it is uniform, Beta, Dirichlet, etc., is irrelevant to the equilibrium result. The key is existence and the i.i.d. structure it implies.

---

## 6. Implication for LLMs

The common prior assumption is actually *more naturally satisfied* by LLMs than by human populations:

- All instances of the same model share identical weights — a literal common prior over responses.
- With temperature sampling, instances are i.i.d. draws from the same distribution conditional on the prompt — conditional independence holds exactly.
- Impersonally informative: if two instances give the same answer, they've sampled from the same region of the output distribution, so their predictions about others should agree.

The non-trivial condition is **stochastic relevance**: does a model's answer shift its predictions about others' answers? For human-like opinion questions, probably yes (false consensus effect has an analog in LLMs — models that output X tend to predict others will output X more often). For questions where RLHF forces convergence to a single answer, stochastic relevance may be weak, which is precisely where BTS is least powerful — and that fact is itself informative.

---

## 7. Summary

The common prior is **necessary** (as the de Finetti representation of exchangeability) but not as an explicit input — only as a structural property of the population. The scoring rule itself requires no knowledge of the prior. The truly essential conditions are:

1. Exchangeable opinions (common prior exists, but its form doesn't matter)
2. Stochastic relevance (different opinions → different beliefs about population)
3. Large population (law of large numbers)

The intuition: BTS works because your true opinion is the one most likely to be "surprisingly common" — your own answer is evidence that the true population frequency of that answer is higher than others expect. This logic holds for any population with an exchangeable belief structure, regardless of the specific prior.
