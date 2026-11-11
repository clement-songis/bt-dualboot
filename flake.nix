{
  description = "Sync Bluetooth for dualboot Linux and Windows";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python3;
        pyproject = (pkgs.lib.importTOML ./pyproject.toml).tool.poetry;

        package = python.pkgs.buildPythonApplication {
          pname = pyproject.name;
          inherit (pyproject) version;
          pyproject = true;
          src = ./.;

          build-system = [ python.pkgs.poetry-core ];

          # Runtime system dependency (Windows registry access)
          propagatedBuildInputs = [ pkgs.chntpw ];

          pythonImportsCheck = [ "bt_dualboot" ];

          meta = {
            inherit (pyproject) description homepage;
            license = pkgs.lib.licenses.mit;
            mainProgram = "bt-dualboot";
            platforms = pkgs.lib.platforms.linux;
          };
        };
      in
      {
        packages.default = package;
        packages.bt-dualboot = package;

        devShells.default = pkgs.mkShell {
          inputsFrom = [ package ];
          packages = [
            (python.withPackages (
              ps: with ps; [
                pytest
                pytest-watch
                pytest-snapshot
                black
                autopep8
                flake8
              ]
            ))
            pkgs.docker
            pkgs.docker-compose
          ];
        };

        apps.default = {
          type = "app";
          program = pkgs.lib.getExe package;
        };
      }
    );
}
