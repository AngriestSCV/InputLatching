{ lib
, pkgs
, python3Packages
}:

python3Packages.buildPythonApplication rec {
  pname = "input-latching-ui";
  version = "0.1";

  # Use the current directory as source (the directory containing default.nix)
  src = ./.;

  # Python runtime deps your app needs
  propagatedBuildInputs = with python3Packages; [
    PySide6
    evdev
  ];

  # If your app has additional non-python runtime deps (e.g. pkg-config, Qt dev),
  # add them here:
  nativeBuildInputs = with pkgs; [ ];

  # If you don't have setup.py/pyproject, you can supply a small installPhase that
  # just copies files and creates a wrapper script. The default build should work
  # for most projects that include setup.py or use standard Python packaging.
  meta = with lib; {
    description = "Qt Quick (PySide6) UI for input latching";
    license = licenses.mit; # change if needed
    maintainers = [];
  };
}
