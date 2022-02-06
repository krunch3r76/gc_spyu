# gc_spyu
Obtain cpu information i.e. model information from providers and persistently store for later retrieval. Optionally, pry into topology information.


For information on the global supercomputer that is Golem and how to run or engineer apps on it, visit https://www.golem.network

For a listing of providers to inspect, visit https://stats.golem.network or invoke my gc__listoffers (https://github.com/krunch3r76/gc__listoffers)

# installation
```bash
$ git clone https://github.com/krunch3r76/gc_spyu.git
$ cd gc_spyu
(gc_spyu)$ git checkout v0.0.4
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
(myvenv)$ ./spyu.py --disable-logging --spy etam q53 --add-topology
```
## to inspect collossus, odra, and whirlwind on testnet, subnet public-beta
```bash
(myvenv)$ ./spyu.py --disable-logging --subnet-tag public-beta --spy collossus odra whirlwind --add-topology
```

## to use the gc__filterms / gc__listoffers environment setting
```bash
(myvenv)$ GNPROVIDER=['0x3dd491','0xcef890','etam'] ./spyu --add-topology
```
# CREDITS
The topology information is taken by running the latest version of openmpi's hwloc. For more information on hwloc, visit: https://www.open-mpi.org/projects/hwloc/. As more CPUs etc topologies emerge, the app is able to update to the latest version by rebuilding the gvmi image from the included Dockerfile. For more on how to rebuild a Golem image, visit https://www.golem.network

utils.py from yapapi examples was utilized to start the Golem process and help manage exceptions. To see the original code, browse: https://github.com/golemfactory/yapapi/blob/master/examples/utils.py

## about topology
CPU topology is becoming increasingly important in programming to leverage CPUs to maximum efficiency. gc_spyu empowers golem requestors to obtain detailed topology information on any node for mGLM (milli); thereby empowering developers to inspect cache sizes on nodes to enable writing low level code that aligns with the fastest accessible memory banks!

# MORE
Stay tuned, more to come including graphical topologies (not ascii), historical lookups, and gc_listoffers interop (some interop already implied by filterms).

