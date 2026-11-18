# v0.3 implementation status

This release implements the first useful slice of the improvement plan without pretending that generic computer vision can perfectly recognize every game event.

Implemented: executable discovery through environment variables, the active Python environment, PATH, and user-local locations; structured source inspection; active/upcoming VOD safety; yt-dlp cookies and extractor arguments; resumable downloads; event models and bounded event windows; focus-aware candidates; audio-spike evidence; optional OpenCV frame-change evidence; generic, Valorant, Counter-Strike 2, and shooter profiles; 1080x1920 rendering; crop modes; caption styles; optional normalization and user-supplied music; compatible manifests with evidence and score breakdowns; and regression tests for the safety-critical behavior.

Not claimed: perfect headshot, GTA, or multi-game semantic recognition; automatic publishing; unlimited live clipping; or zero failures. OCR/template matching, true game-specific event classifiers, contact-sheet approval, and a full browser approval UI remain follow-up work. The CLI explicitly records uncertainty and requires human review before publishing.
