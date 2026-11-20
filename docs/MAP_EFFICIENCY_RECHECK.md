# Map efficiency and novelty: second literature check

22 October 2026. The user requested a second check of whether making the lunar
map computationally lighter would be novel. This targeted search included
compressed localization maps, navigation-oriented elevation encodings,
informative terrain features, and spacecraft map-processing software.

## Revised assessment

There is strong evidence that the broad idea is established. More importantly,
retaining terrain information useful for localization under a memory budget is
also established. The earlier suggestion to preserve navigation-relevant
features must therefore be treated as a design objective, not an identified
novel contribution. A concrete new method may still be research, but this review
does not establish one for LANTERN.

## Closer precedents than the first review

### 1. Compact localization maps under memory constraints

Marcin Dymczyk et al., *Keep it brief: Scalable creation of compressed localization
maps*, IROS 2015, DOI 10.1109/IROS.2015.7353722. Optimizes a reduced landmark map
for coverage and localizability within a memory budget. This is terrestrial
visual localization, not lunar elevation matching, but directly precedes the
general task-aware map compression idea. Publisher and author-institution
abstract records verified; full text was not accessed.
[Author-institution record](https://www.research-collection.ethz.ch/items/484b0401-e0d9-4845-a56f-4f426320dbb0),
[publisher record](https://ieeexplore.ieee.org/abstract/document/7353722).

### 2. Compact elevation encoding for terrain-relative navigation

Kristen A. Michaelson, Felix Wang and Renato Zanetti, *Terrain-Relative Navigation
with Neuro-Inspired Elevation Encoding*, IEEE TAES 60(3), 3368-3378, June 2024,
DOI 10.1109/TAES.2024.3362760. The author-hosted manuscript describes a phase
dictionary smaller than the original elevation map, reduced working memory,
measurement rejection and online measurement covariance. This is a particularly
close precedent for combining compact terrain representation and measurement
reliability. It is not a demonstration of our entire lunar camera/altimeter
diagnosis proposal. Author manuscript inspected; publication metadata confirmed
on the authors' publication list. Do not infer the publication year from the
manuscript's placeholder IEEE footer.
[Author manuscript](https://sites.utexas.edu/near/files/2024/01/REVISED_SUBMISSION__Terrain_Relative_Navigation_with_Neuro_Inspired_Elevation_Encoding__TAES_Two_Column_.pdf),
[publication list](https://sites.utexas.edu/near/publications/journal-publications/).

### 3. Variable-resolution planar maps for planetary landing

Corey L. Marcus, Renato Zanetti and Timothy P. Setterfield, *Landing Site Mapping
and Selection with Quadtree Map Using Planar Elements*, Journal of Guidance,
Control, and Dynamics 47(7), 1283-1297, July 2024, DOI 10.2514/1.G007801.
Uses flash-lidar observations during descent to form a variable-resolution
quadtree of planar estimates for landing-site selection. The abstract reports
validation with rocket-powered flight-test data over an artificial lunar
environment. This precedes generic adaptive terrain representation for landing;
its task is site selection rather than our exact registration/trust objective.
Author-hosted abstract and publication metadata verified.
[Author paper](https://sites.utexas.edu/near/wp-content/uploads/sites/6030/2024/04/Marcus_2024_landing-site-mapping-and-selection-w-a-quadtree-map.pdf).

### 4. Efficient active TRN with surface maps and flight hardware

Davis Adams, Vikas Patel and Isaac Rowe, *Active Terrain Relative Navigation with
Surface Mapping Sensors*, AIAA SciTech 2026, NASA record 20250010194. Describes
sparse 3D keypoints, relative/global localization, fusion of successive maps,
and flight-software resource optimization. Full 25-page NASA PDF downloaded;
resource optimization and performance sections inspected. Sections IV.C and V.C
explicitly address memory management and computation. Table 3 reports a
3500x3500 DEM case taking 545 s for gradient/Laplacian methods versus 46.9 s
for ZIG on their descent computer. This is a configuration-specific processing
comparison, not a compression ratio or a benchmark against LANTERN. The
conclusion notes ZIG can introduce greater errors and be less successful with
small overlap. It illustrates a documented efficiency/robustness tradeoff.
[NASA record and paper](https://ntrs.nasa.gov/citations/20250010194).

### 5. Navigation-relevant terrain information

Joshua Vander Hook et al., *Topographical Landmarks for Ground-Level Terrain
Relative Navigation on Mars*, IEEE Aerospace 2022, DOI
10.1109/AERO53065.2022.9843350. Identifies terrain landmarks and evaluates their
localization informativeness through visibility and geometry. It supports the
need to compare with information-aware feature selection; it is not itself
evidence of a lunar compressed-DEM method. Full author-hosted PDF inspected.
[JPL paper](https://www-robotics.jpl.nasa.gov/media/documents/Topographical_Landmarks_for_Ground-Level_Terrain_Relative_Navigation_on_Mars.pdf).

The previously reviewed Schoppmann et al. multiresolution planetary mapping,
Jin et al. adaptive-resolution mapping, and Sanlan et al. cheaper terrain
measurement processing remain relevant. This second check adds more direct
competitors rather than replacing those references.

## What this means for a conference paper

"Smaller map", "keep informative regions", "adaptive resolution", and "compact
encoding plus uncertainty" are insufficient standalone novelty claims. A new
implementation or application can have engineering value without being a new
method. Applying an existing technique to the Moon does not automatically
establish a research contribution.

Before selecting a paper claim:

1. Specify exactly what changes: encoding, feature selection, map query,
   matching algorithm, or uncertainty propagation. These are different problems.
2. Profile whether map storage, RAM, matching or sensor processing is actually
   limiting our system. The current matcher already uses elevation grids.
3. Select the closest baseline for that component. Quadtree landing-site
   selection and compressed visual landmarks are adjacent, not interchangeable
   implementations of lidar-to-DEM localization.
4. Test the full resource/accuracy/reliability frontier on identical inputs and
   hardware, including decoding, metadata and peak working memory. Compare at
   equal budgets, with reserved areas, missing terrain and map errors.
5. Claim a new method only after the mechanism differs from prior work and the
   evidence supports the claimed improvement. Retain negative results.

A possible investigation is whether approximation uncertainty can be propagated
through map matching into sensor-integrity decisions while bounding additional
false confident matches under a memory limit. This is a research question to
check, not a verified open gap or a promised conference contribution. We should
not keep renaming combinations of established ideas as new methods.

The strongest defensible conclusion is that this is an established research
area in which a specific improvement could be publishable. No currently
implemented map-efficiency innovation has been established as novel for LANTERN.
No training or simulation was started for this review.

## Access and provenance

The NASA PDF exceeded the browser tool's size limit and was downloaded directly
from NTRS for local text inspection. The local PDF is retained under
`out/literature/20261022_map_efficiency_recheck/`. Other sources were inspected at
the access levels noted above. Search-engine crawl dates were not treated as
publication dates. This is a targeted novelty audit, not a proof that no narrower
unpublished or unindexed method exists.
