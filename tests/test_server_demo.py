from server.server import _parse_demo_output


def test_parse_demo_output_extracts_solver_metrics():
    output = """
============================================================
  AeroGaze AI  -  offline celestial positioning
============================================================
  true position    : +38.9900, -77.0300
  RECOVERED        : +38.9884, -77.0279
  error            : 0.25 km
  stars detected   : 40
  inlier matches   : 39
  solve residual   : 10.3 arcsec
============================================================
"""

    parsed = _parse_demo_output(output)

    assert parsed["recovered_lat"] == 38.9884
    assert parsed["recovered_lon"] == -77.0279
    assert parsed["error_km"] == 0.25
    assert parsed["stars_detected"] == 40
    assert parsed["inlier_matches"] == 39
    assert parsed["residual_arcsec"] == 10.3
