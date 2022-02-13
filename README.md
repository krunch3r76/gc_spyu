# gc_spyu
espy cpu model information from specific providers and persistently store for later retrieval.

The current Golem network conceals the model information of providers. While obtaining model specifications is possible utilizing the yapapi repository examples (Golem code), it only randomly selects providers.  gc_spyu solves this problem of only random specifications by facilitating the procurement of specific provider's (cpu) model information.

For information on the global supercomputer that is Golem and how to run or engineer apps on it, visit https://www.golem.network

For a listing of providers to inspect, visit https://stats.golem.network or invoke my gc__listoffers (https://github.com/krunch3r76/gc__listoffers)

# first installation
```bash
$ git clone https://github.com/krunch3r76/gc_spyu.git
$ cd gc_spyu
(gc_spyu)$ git checkout v0.0.6
(gc_spyu)$ python -m venv myvenv
(gc_spyu)$ . myvenv/bin/activate
(myvenv)$ pip install -r requirements.txt
```

# upgrade installation removing current installation
```bash
(gc_spyu)$ git clean -dfx
(gc_spyu)$ git clone https://github.com/krunch3r76/gc_spyu.git
(gc_spyu)$ git checkout v0.0.6
```

# DEMO

https://user-images.githubusercontent.com/46289600/152745449-44dd2397-a4ea-41e0-8584-9eddccda1427.mp4


# USAGE

## invocation
```bash
(myvenv)$ ./gc_spyu.py --spy <space delimited list of nodes>
```  
## to inspect etam and q53 on testnet, subnet devnet-beta
```bash
(myvenv)$ ./gc_spyu.py --spy etam q53
```
## to inspect collossus, odra, and whirlwind on testnet, subnet public-beta
```bash
(myvenv)$ ./gc_spyu.py --disable-logging --subnet-tag public-beta --spy collossus odra whirlwind
```

## to use the gc__filterms / gc__listoffers environment setting
```bash
(myvenv)$ GNPROVIDER=['0x3dd491','0xcef890','etam'] ./gc_spyu
```
# TROUBLESHOOTING
If the script fails to run and you see errors including:
```bash
ValueError: loop argument must agree with lock
AttributeError: 'SmartQueue' object has no attribute '_new_items'
```
please use a version of Python < 3.10.
```bash
python3.9 -m myvenv
# etc
```

# CREDITS
utils.py from yapapi examples was utilized to start the Golem process and help manage exceptions. To see the original code, browse: https://github.com/golemfactory/yapapi/blob/master/examples/utils.py

data_directory.py module to get a cross-platform specific data directory was adapted from code shared by an Honest Abe on a discussion at: https://www.py4u.net/discuss/161917


# MORE
Stay tuned for gc_listoffers interop (some interop already implied by filterms).

# see also
https://github.com/golemfactory/yapapi/tree/master/examples/scan

