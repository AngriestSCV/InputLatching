{ pkgs ? import <nixpkgs> {} }:

let
  pname = "input-latching";
  version = "0.1";
  py = pkgs.python3;                         # change to python310 if desired
  pyPkgs = py.pkgs;
in

pkgs.stdenv.mkDerivation {
  inherit pname version;
  src = ./.;

  nativeBuildInputs = with pkgs; [ makeWrapper ];
  buildInputs = with pkgs; [
    py
    py.pkgs.pyside6
    py.pkgs.evdev
  ];

  # No building step; just install files and create a wrapper binary.
  buildPhase = ''
    rm -rf result
  '';

  installPhase = ''
    mkdir -p $out/lib/${pname}-${version}
    cp -r --preserve=links ./* $out/lib/${pname}-${version}/
    mkdir -p $out/bin

    cat > $out/bin/${pname} <<'EOF'
#!${py}/bin/python3

import os, sys, runpy
# Add our package dir to sys.path
pkgdir = os.path.join(os.path.dirname(__file__), "..", "lib", "${pname}-${version}")
sys.path.insert(0, pkgdir)
# print("Current path: ", sys.path)
runpy.run_path(os.path.join(pkgdir, "InputLatching.py"), run_name="__main__")

EOF

    chmod a+x $out/bin/${pname}

    # Wrap the script to ensure PYTHONPATH/PATH include needed runtime libs
    wrapProgram $out/bin/${pname} \
      --set PYTHONPATH "$out/lib/${pname}-${version}:$PYTHONPATH"

    # Install desktop entry
    mkdir -p $out/share/applications
    cp ${pname}.desktop $out/share/applications/

    # Install icon
    mkdir -p $out/share/icons/hicolor/256x256/apps
    cp resources/icon.png $out/share/icons/hicolor/256x256/apps/${pname}.png

  '';

  # metadata
  meta = with pkgs.lib; {
    description = "Input latching GUI (PySide6) - local development build";
    license = licenses.gpl3;
    maintainers = with maintainers; [ ];
  };
}
