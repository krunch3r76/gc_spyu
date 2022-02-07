# gc_spyu
Espy cpu model information from specific providers and persistently store for later retrieval. Optionally, pry into topology information.

The current Golem network conceals the model information of providers. While obtaining model specifications is possible utilizing the yapapi repository examples (Golem code), it only randomly selects providers.  gc_spyu solves this problem of only random specifications by facilitating the procurement of specific provider's model information.

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
this video demonstrates the add-topology feature of the current version of gc_spyu. however, gathering topology information will be removed in the next version and but added as a subproject. topology information is not accurately reported as of this writing.

# USAGE

## invocation
```bash
(myvenv)$ ./spyu.py --spy <space delimited list of nodes>
```  
## to inspect etam and q53 on testnet, subnet devnet-beta
```bash
(myvenv)$ ./spyu.py --spy etam q53
```
## to inspect collossus, odra, and whirlwind on testnet, subnet public-beta
```bash
(myvenv)$ ./spyu.py --disable-logging --subnet-tag public-beta --spy collossus odra whirlwind
```

## to use the gc__filterms / gc__listoffers environment setting
```bash
(myvenv)$ GNPROVIDER=['0x3dd491','0xcef890','etam'] ./spyu
```
# CREDITS
utils.py from yapapi examples was utilized to start the Golem process and help manage exceptions. To see the original code, browse: https://github.com/golemfactory/yapapi/blob/master/examples/utils.py


## about topology
gc_spyu is capable of running a topology inspector (lstopo of the hwloc suite from open-mpi). CPU topology is becoming increasingly important in programming to leverage CPUs to maximum efficiency. gc_spyu has this capability in the future where provider runs will occur without any virtualization or with complete pass thru. When pass-thru comes to golem, requestors shall be be able to obtain detailed topology information on any node for mGLM (milli); thereby empowering developers to inspect cache sizes on nodes to enable writing low level code that aligns with the fastest accessible memory banks!

The topology information is gathered by running the latest version of openmpi's hwloc on the provider vm. For more information on hwloc, visit: https://www.open-mpi.org/projects/hwloc/. As more CPUs etc topologies emerge, the app is able to update to the latest version by rebuilding the gvmi image from the included Dockerfile. For more on how to rebuild a Golem image, visit https://www.golem.network

# MORE
Stay tuned, more to come including graphical topologies (not ascii), historical lookups, and gc_listoffers interop (some interop already implied by filterms).

# see also
https://github.com/golemfactory/yapapi/tree/master/examples/scan

