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
      in {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.linuxHeaders  # needed for evdev build
          ];

          shellHook = ''
            echo "Run ui.py. sudo or input group required"
          '';
        };
      });
}

