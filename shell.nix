{
  pkgs ? import <nixpkgs> { },
}:
let
  cache = toString ./.nix-files;

  pythonPackages = pkgs.python311Packages;
in
with pkgs;
mkShell rec {

  venvDir = toString "/.venv";

  nativeBuildInputs = [
    gcc-unwrapped
    qt6.qtwayland
    pythonPackages.python
    pythonPackages.pip
    pythonPackages.numpy
    pythonPackages.pandas
    pythonPackages.matplotlib
    pythonPackages.dash
    pythonPackages.plotly
    pythonPackages.bleak
    pythonPackages.dash-bootstrap-components
  ];
}
