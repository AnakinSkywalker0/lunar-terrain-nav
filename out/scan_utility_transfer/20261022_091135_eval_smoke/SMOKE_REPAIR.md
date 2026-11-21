# Smoke verification note

All 15 simulations completed. The first independent terrain check assumed bilinear Unity height interpolation and failed with a 0.274 m maximum difference. A direct Unity probe at the largest difference verified triangle interpolation. Corrected the Python verifier to use terrain triangles, with a height-quantization bound for sample/centre subtraction. All 15 cases and 150 scans then passed. No terrain source, raw results, model, policy, controller or runtime adapter changed.
