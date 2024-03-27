## Installation
the opennem dependencies are a bit wacky. Installing normally will cause "cython" related errors while installing pyyaml==5.4.1, however this is the version required by opennem.

The only solution I have found is 

`pip install "cython<3.0" wheel && pip install --no-build-isolation "pyyaml==5.4.1"`

and then

`pip install opennem urllib3==1.26.18`

This works on python==3.11.8, likely works with other versions of python too. The main thing is that you need to do this in stages, it will not work if you plonk all those dependenceis into a pipfile.