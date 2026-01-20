{
  description = "Sync Bluetooth for dualboot Linux and Windows";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      poetry2nix,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication overrides;

        systemDeps = with pkgs; [
          chntpw
        ];

        package = mkPoetryApplication {
          projectDir = ./.;
          overrides = overrides.withDefaults (
            final: prev: {
              libfaketime = prev.libfaketime.overridePythonAttrs (old: {
                buildInputs = (old.buildInputs or [ ]) ++ [ prev.setuptools ];
              });
            }
          );
          propagatedBuildInputs = systemDeps;
        };
      in
      {
        packages.default = package;
        packages.bt-dualboot = package;

        devShells.default = pkgs.mkShell {
          inputsFrom = [ package ];
          buildInputs = with pkgs; [
            # poetry
            docker
            docker-compose
          ];
        };

        apps.default = {
          type = "app";
          program = "${package}/bin/bt-dualboot";
        };
      }
    );
}
