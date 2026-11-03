# SYNAPSE evidence-assessment slice

Added `src/synapse/reasoning/assessment/` with a deterministic assessment engine and a structural verifier.

The result classifies the graph's existing evidence-link roles for a claim. This does **not** score source reliability or prove the underlying proposition true. Context-only and no-link claims are inconclusive. The verifier checks exact link membership, role, duplicates, and computed status.

This is an incremental patch over the uploaded archive. Review it in your repository and run the project tests before merging.
