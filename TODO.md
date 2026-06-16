# TODO

## Geography Quality

- Many simulated pings are landing in water. Add a land/water constraint before treating the simulation as visually credible.

Possible fixes:

- constrain sampled home points to land polygons rather than circular jitter around anchors
- filter POI centroids and route interpolation points against a land mask
- snap over-water route interpolation points back toward land or switch to a coarse corridor/waypoint model
- add a QA layer that reports percentage of pings by land/water status

This does not block the first full pipeline test, but it should be addressed before we use the visualization as a serious movement demo.
