{
  description = "Latch Input Tool with evdev + tkinter";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        python = pkgs.python3;

        pythonEnv = python.withPackages (ps: with ps; [
          evdev
          pyinstaller
          pyside6
        ]);

        qtdeclarative = (pkgs.lib.findFirst
          (p: (p.pname or "") == "qtdeclarative")
          (throw "qtdeclarative not found in pyside6 buildInputs")
          pkgs.python3Packages.pyside6.buildInputs).out;

      in {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.linuxHeaders  # needed for evdev build
          ];

          shellHook = ''
            export QML_IMPORT_PATH="${qtdeclarative}/lib/qt-6/qml"
            echo "Run InputLatching.py. input group required"
          '';
        };
      });
}
