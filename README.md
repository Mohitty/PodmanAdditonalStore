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
  * add the path of ./additonalstore_overlay or ./additonalstore_vfs to the additionalimagestore field in the file, depending on the default driver.
  * change the value of driver field to overlay or vfs accordingly.
* Run command `sudo podman images` to list images. This should output fedora image as an entry from additonal store.
* Run command `sudo podman run -it docker.io/library/fedora /bin/bash` . This will start the container and give an interactive shell.
* Run command `sudo podman ps` . This should list the above running container.
