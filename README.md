# genowl

The OWL ROS message and service generator.

## Examples for generating messages with dependencies

```console
./scripts/genmsg_owl.py -p std_msgs -Istd_msgs:`rospack find std_msgs`/msg -o gen `rospack find std_msgs`/msg/String.msg
./scripts/genmsg_owl.py -p geometry_msgs -Istd_msgs:`rospack find std_msgs`/msg -Igeometry_msgs:`rospack find geometry_msgs`/msg -o gen `rospack find geometry_msgs`/msg/PoseStamped.msg
```
