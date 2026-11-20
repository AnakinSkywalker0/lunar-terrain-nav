#!/bin/bash
cd "$(dirname "$0")"
for s in "ml2_control_noise.py" "ml2_fresh.py" "ml2_ablate.py" "ml2_classifier_tests.py" "ml2_compare.py --n 100"; do
  n=$(echo $s | cut -d' ' -f1 | sed 's/.py//')
  echo "START $s $(date -Is)" >> runall.status
  python sim/$s > $n.log 2>&1
  echo "END $s exit=$? $(date -Is)" >> runall.status
done
echo ALLDONE >> runall.status
