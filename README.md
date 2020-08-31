# PodmanAdditonalStore
This repo investigates the directory structure for additonal stores required by podman.
Podman uses overlay driver for root users and vfs driver for non-root users by default. There are two sub-directories containing the corresponding files for both drivers. 

The two directories containes exploded rootfs of fedora image and required files to allow podman to use it to launch a container from it.

The basic structure of the directories is:
* ($DriverName) : contains the exploded rootfs of container image.
* ($DriverName)-images : contains image manifest list.
* ($DriverName)-layers : contains layer checksum.

## Usage
* Clone the repository
* Edit the /etc/containers/storage.conf file
  * change the value of driver field to overlay or vfs to override default driver.
  * add the path of ./additonalstore_overlay or ./additonalstore_vfs (depending on the driver set above) to the additionalimagestore field in the file
* Run command `sudo podman images` to list images. This should output fedora image as an entry from additonal store.
* Run command `sudo podman run -it docker.io/library/fedora /bin/bash` . This will start the container and give an interactive shell.
* Run command `sudo podman ps` . This should list the above running container.

## Let's see how Podman works and uses Additional stores in detail

### Where are the images stored?

When you run podman images, podman looks for the images already pulled on the system. The images for podman and docker are stored in different locations. Hence, podman images won’t list the images previously pulled by docker. The images for podman are stored in /var/lib/containers for root users and ~/.local/share/containers for non-privileged users. The storage location is different from docker ( /var/lib/docker ) because it’s storage structure is based on the OCI standards. The images for docker and podman are compatible, but they are stored differently on the system. We will get into the structure of the storage in the post later.

### Libpod : Home of Podman

Podman uses containers/storage as it’s storage backend and containers/image to manipulate images.

The core object in containers/storage is the Store object. It encapsulates the storage structure and stores all the images and layers present on the system along with other relevant metadata.

The image object and layer object in the storage library encapsulates all the information related to an image and a layer respectively.
Storage

We will discuss the storage structure for overlay driver only in this post. Let’s look at an example structure of /var/lib/containers/storage (the digest values are shown only upto 6 hexadecimal digits for compactness). The following store contains the ubuntu:latest image pulled from docker hub.

/var/lib/containers/storage

├── libpod

│ └── bolt_state.db

├── mounts

├── overlay

│ ├── 2ce3c1

│ │ ├── diff

│ │ ├── empty

│ │ ├── link

│ │ ├── merged

│ │ └── work

│ ├── 4cc8a6

│ │ ├── diff

│ │ ├── link

│ │ ├── lower

│ │ ├── merged

│ │ └── work

│ ├── 720c33

│ │ ├── diff

│ │ ├── link

│ │ ├── lower

│ │ ├── merged

│ │ └── work

│ ├── compat214010866

│ │ ├── lower1

│ │ ├── lower2

│ │ ├── merged

│ │ ├── upper

│ │ └── work

│ ├── compat567238191

│ │ ├── lower1

│ │ ├── lower2

│ │ ├── merged

│ │ ├── upper

│ │ └── work

│ ├── da0180

│ │ ├── diff

│ │ ├── link

│ │ ├── lower

│ │ ├── merged

│ │ └── work

│ └── l

│ │ ├── DCA3F65L7EAFZTJ55MTGPQMDSM -> ../4cc8a6/diff

│ │ ├── JJG53NDRFWK4UKBVGWDMYNB3L3 -> ../da0180/diff

│ │ ├── NQZ7WILONDZ22PEBUGEZ3MOFID -> ../720c33/diff

│ │ └── VAEMYZJDRVJZDW6ZIJO76NEVCQ -> ../2ce3c1/diff

├── overlay-containers

│ ├── containers.json

│ └── containers.lock

├── overlay-images

│ ├── 4e2eef

│ │ ├── =bWFY3YTU=

│ │ ├── =bWFZTU=

│ │ ├── =c2hM2M=

│ │ ├── =c2lZTU=

│ │ └── manifest

│ ├── images.json

│ └── images.lock

├── overlay-layers

│ ├── 2ce3c1.tar-split.gz

│ ├── 4cc8a6.tar-split.gz

│ ├── 720c33.tar-split.gz

│ ├── da0180.tar-split.gz

│ ├── layers.json

│ └── layers.lock

├── storage.lock

├── tmp

├── userns.lock

└── volumes


We will discuss the role of directories marked bold in the above directory tree.

**overlay dir**: The unpacked content of layers are stored in this directory. For each layer, it’s exploded rootfs is store in overlay/<digest>/diff, where the <digest> is the sha256 digest of uncompressed content of the layer. For each layer, a random id is stored in overlay/<digest>/link file.

The overlay/l dir contains the symlinks to the exploded rootfs of layers in overlay/<digest>/diff . The name of the symlink is same as the random id of the layer stored in the corresponding overlay/<digest>/link file.

The overlay/<digest>/lower file stores the random id of the parent layer (and their parent layer’s random id) separated by ‘:’

The purpose of storing the symlinks in overlay/l and random id of parents in overlay/<digest>/lower files will be explained later.

The overlay/<digest>/(merge/upper/work) are meant for overlay driver to use as work and merge and upper dir.

**overlay-containers dir**: This stores the ‘write-able’ layers of the running container.

**overlay-images dir**: This stores the relevant metadata about images in the local system. For each image in the local store, it stores various configuration and manifest files inside overlay-images/<digest>/* ,where <digest> is the sha256 sum of image.

Apart from this, there is a images.json file. This stores the relevant metadata about all the images in the corresponding store as json objects.

**overlay-layers dir**: It contains a layers.json file, which stores the relevant metadata of all the layers in the corresponding store as json objects.

I’ll explain the content of images.json and layers.json file later in the post.

### How Podman uses the store

Let’s see a few example commands to learn how different files are used by podman:

When we run podman images, podman extracts information from images.json file in overlay-images dir. It prints the images listed in this file.

When we run podman run ubuntu:latest it searches for ubuntu image in images.json file. If it not present, it pulls the image from the registry. Once the image is present in the local system, it retrieves the relevant metadata from images.json and layers.json files. Then it mounts all the layers and adds a write-able layer on top. For mounting the images, it looks for the top most layer of the image (stored in images.json). It retrieves the random id of this layer from the overlay/<digestoftoplayer>/link file and of all the parent layers from the overlay/<digestoftoplayer>/lower file. It then mounts these layers from overlay/l/<randomidoflayer>

When we run podman ps command, it looks into the overlay-containers/containers.json file and list all running containers in it.

### Images.json and Layers.json:

Finally, let’s have a look at the content of images.json and layers.json files. Each store, whether read-write or read-only(see next section) has their own images.json and layers.json file.For each image, images.json stores the following metadata as json object.
1. Image id
2. Name
3. Top most Layer id
4. Creation time

For each layer in the store, layers.json stores the following metadata as json object:
1. Layer id
2. Creation time
3. Compressed digest
4. Compressed size
5. Uncompressed digest
6. Uncompressed size
7. Parent layer

### Concept of Additional Stores

Earlier I stated that the images are stored in /var/lib/containers/storage This is the (only) read-write image store of podman. There can be (any number of) read-only image stores, called additional stores. To use an additional store, add the absolute path to the configuration file of podman, which is located at /etc/containers/storage.conf.

The reason I explained the content of only a few directories present in var/lib/containers/storage is that, we only need these directories and files to be necessarily present in a directory for it to be a valid additional store. It may contain all the files that are present in read-write store, but they are not necessarily required.

Hence an additional store containing the ubuntu image would look like:

/path/to/additional/store

├── overlay

│ ├── 2ce3c1

│ │ ├── diff

│ │ ├── link

│ ├── 4cc8a6

│ │ ├── diff

│ │ ├── link

│ │ ├── lower

│ ├── 720c33

│ │ ├── diff

│ │ ├── link

│ │ ├── lower

│ ├── da0180

│ │ ├── diff

│ │ ├── link

│ │ ├── lower

│ └── l

│ │ ├── DCA3F65L7EAFZTJ55MTGPQMDSM -> ../4cc8a6/diff

│ │ ├── JJG53NDRFWK4UKBVGWDMYNB3L3 -> ../da0180/diff

│ │ ├── NQZ7WILONDZ22PEBUGEZ3MOFID -> ../720c33/diff

│ │ └── VAEMYZJDRVJZDW6ZIJO76NEVCQ -> ../2ce3c1/diff

├── overlay-images

│ ├── 4e2eef

│ │ ├── =bWFY3YTU=

│ │ ├── =bWFZTU=

│ │ ├── =c2hM2M=

│ │ ├── =c2lZTU=

│ │ └── manifest

│ ├── images.json

│ └── images.lock

├── overlay-layers

│ ├── layers.json

│ └── layers.lock

Note the following changes from the read-write store: We don’t have upper, merge and work directories in overlay/<digest>/ directory any more. This is because it is a read only store, hence we can’t use them with overlay. Instead podman mounts these layers in the read-write store’s overlay directory.

Additional stores is an awesome feature of podman. Imagine you setup a read-only image store. You can then use the store over a NFS, to run images without having to pull the images into local system. As part of my GSoC (2020) project, I created an additional store in CVMFS repository from which we can run containers without pulling them to local system.

### Additional Resources:

* [Working with containers/storage library](https://www.redhat.com/en/blog/working-container-storage-library-and-tools-red-hat-enterprise-linux)
* [Working with images stores in podman](https://www.redhat.com/sysadmin/image-stores-podman)
* [Behind the scenes of rootless podman containers](https://podman.io/new/2020/03/03/new.html)
* [Migrating from docker to podman](https://podman.io/new/2019/11/05/new.html)
