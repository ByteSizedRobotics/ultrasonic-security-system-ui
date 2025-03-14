{
  pkgs ? import <nixpkgs> { },
}:
let
  cache = toString ./.nix-files;

  requirements = toString ./requirements.txt;

  pythonPackages = pkgs.python311Packages;
  rustToolchain = "stable";
in
with pkgs;
mkShell rec {

  venvDir = toString "/.venv";

  nativeBuildInputs = [
    gcc-unwrapped
    qt6.qtwayland
    pythonPackages.python
    pythonPackages.pip
    pythonPackages.venvShellHook
    pythonPackages.numpy
    pythonPackages.pandas
    pythonPackages.matplotlib
    pythonPackages.dash
    pythonPackages.plotly
    pythonPackages.bleak
  ];

  postVenvCreation = ''
    unset SOURCE_DATE_EPOCH
    pip install -r ${requirements}
  '';

  shellHook = ''
    unset SOURCE_DATE_EPOCH
    export LD_LIBRARY_PATH=${lib.makeLibraryPath [ stdenv.cc.cc ]}
    source ${venvDir}/bin/activate
  '';
}
