cmake_minimum_required(VERSION 2.8.3)
project(genowl)
find_package(catkin REQUIRED COMPONENTS genmsg actionlib_msgs)

catkin_package(
  CATKIN_DEPENDS genmsg
  CFG_EXTRAS genowl-extras.cmake
)

add_subdirectory(scripts)

file(WRITE ${CATKIN_DEVEL_PREFIX}/${GENMSG_LANGS_DESTINATION}/genowl "OWL")
install(FILES ${CATKIN_DEVEL_PREFIX}/${GENMSG_LANGS_DESTINATION}/genowl
  DESTINATION ${GENMSG_LANGS_DESTINATION})

catkin_python_setup()
