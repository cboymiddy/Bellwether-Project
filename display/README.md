# Display-layer mapping (not part of the frozen pipeline)

- `literal_labels.csv`: display wording for every positive literal. A negation is shown as `NOT: <display_statement>`.
  Astronomy 'separation' literals are the folded difference in ecliptic longitude (the pool's own text says 'angular separation', which is inaccurate); the mapping corrects the wording only.
- `year_names.csv`: the club name used in each election year for MLB, NFL, NBA and NHL, from the event tables and the Wikipedia champions list as fetched in Phase 1.
- The frozen pool files, matrices, ranking and hashes are untouched (checked against `freeze.yaml`).
- Not covered: Olympic host names are already the names used then (e.g. Soviet Union, West Germany) in the event table.
