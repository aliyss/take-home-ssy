with import <nixpkgs> {
  config = {
  };
};
  mkShell {
    name = "impurePythonEnv";
    buildInputs = [
      # Python
      python311Packages.python
      python311Packages.pip
      python311Packages.pillow
      python311Packages.numpy
      python311Packages.venvShellHook

      # In this particular example, in order to compile any binary extensions they may
      # require, the Python modules listed in the hypothetical requirements.txt need
      # the following packages to be installed locally:
      nsjail
      swig4
      blas
      ninja
      taglib
      openssl
      git
      libxml2
      libxslt
      libzip
      zlib
    ];

    venvDir = "./.venv";
    postVenvCreation = ''
      unset SOURCE_DATE_EPOCH
      pip install -U pip setuptools wheel
      pip install -r requirements.txt
    '';

    postShellHook = ''
      export SOURCE_DATE_EPOCH=315532800

    '';

    preferLocalBuild = true;
  }
