# gc_spyu
a golem node topology inspector

CPU topology is becoming increasingly important in programming to leverage CPUs to maximum efficiency. gc_spyu empowers golem requestors to obtain detailed topology information on any node for micro glm.

# installation
```bash
$ git clone https://github.com/krunch3r76/gc_spyu.git
$ cd gc_spyu
(gc_spyu)$ git checkout v0.0.1
(gc_spyu)$ python -m venv myvenv
(gc_spyu)$ . myvenv/bin/activate
(myvenv)$ pip install -r requirements.txt
```

# DEMO
https://user-images.githubusercontent.com/46289600/152594180-054dad3a-4c53-4103-857e-2baf6c4e84b6.mp4


# USAGE

## invocation
```bash
(myvenv)$ ./spyu.py --spy <space delimited list of nodes>
```  
## to inspect etam and q53 on testnet, subnet devnet-beta
```bash
(myvenv)$ ./spyu.py --disable-logging --spy etam q53
```
## to inspect collossus, odra, and whirlwind on testnet, subnet public-beta
```bash
(myvenv)$ ./spyu.py --disable-logging --subnet-tag public-beta --spy collossus odra whirlwind
```

Stay tuned, more to come including graphical topologies (not ascii) and gc_listoffers interop.
