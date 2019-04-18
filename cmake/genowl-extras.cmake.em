@[if DEVELSPACE]@
# location of scripts in develspace
set(GENOWL_BIN_DIR "@(CMAKE_CURRENT_SOURCE_DIR)/scripts")
@[else]@
# location of scripts in installspace
set(GENOWL_BIN_DIR "${genowl_DIR}/../../../@(CATKIN_PACKAGE_BIN_DESTINATION)")
@[end if]@

set(GENMSG_OWL_BIN ${GENOWL_BIN_DIR}/genmsg_owl.py)
set(GENSRV_OWL_BIN ${GENOWL_BIN_DIR}/gensrv_owl.py)
set(GENPKG_OWL_BIN ${GENOWL_BIN_DIR}/genpkg_owl.py)

macro(_generate_msg_owl ARG_PKG ARG_MSG ARG_IFLAGS ARG_MSG_DEPS ARG_GEN_OUTPUT_DIR)

  #Append msg to output dir
  set(GEN_OUTPUT_DIR "${ARG_GEN_OUTPUT_DIR}/msg")
  file(MAKE_DIRECTORY ${GEN_OUTPUT_DIR})
  #Create input and output filenames
  get_filename_component(MSG_SHORT_NAME ${ARG_MSG} NAME_WE)

  set(MSG_GENERATED_NAME ${MSG_SHORT_NAME}.owl)
  set(GEN_OUTPUT_FILE ${GEN_OUTPUT_DIR}/${MSG_GENERATED_NAME})

  add_custom_command(OUTPUT ${GEN_OUTPUT_FILE}
    DEPENDS ${GENMSG_OWL_BIN} ${ARG_MSG} ${ARG_MSG_DEPS}
    COMMAND ${CATKIN_ENV} ${PYTHON_EXECUTABLE} ${GENMSG_OWL_BIN} ${ARG_MSG}
    ${ARG_IFLAGS}
    -p ${ARG_PKG}
    -o ${GEN_OUTPUT_DIR}
    COMMENT "Generating OWL from MSG ${ARG_PKG}/${MSG_SHORT_NAME}"
    )

  list(APPEND ALL_GEN_OUTPUT_FILES_py ${GEN_OUTPUT_FILE})

endmacro()

#todo, these macros are practically equal. Check for input file extension instead
macro(_generate_srv_owl ARG_PKG ARG_SRV ARG_IFLAGS ARG_MSG_DEPS ARG_GEN_OUTPUT_DIR)

  #Append msg to output dir
  set(GEN_OUTPUT_DIR "${ARG_GEN_OUTPUT_DIR}/srv")
  file(MAKE_DIRECTORY ${GEN_OUTPUT_DIR})

  #Create input and output filenames
  get_filename_component(SRV_SHORT_NAME ${ARG_SRV} NAME_WE)

  set(SRV_GENERATED_NAME ${SRV_SHORT_NAME}.owl)
  set(GEN_OUTPUT_FILE ${GEN_OUTPUT_DIR}/${SRV_GENERATED_NAME})

  add_custom_command(
    OUTPUT ${GEN_OUTPUT_FILE}
    DEPENDS ${GENSRV_OWL_BIN} ${ARG_SRV} ${ARG_MSG_DEPS}
    COMMAND ${CATKIN_ENV} ${PYTHON_EXECUTABLE} ${GENSRV_OWL_BIN} ${ARG_SRV}
    ${ARG_IFLAGS}
    -p ${ARG_PKG}
    -o ${GEN_OUTPUT_DIR}
    COMMENT "Generating Python code from SRV ${ARG_PKG}/${SRV_SHORT_NAME}"
    )

  list(APPEND ALL_GEN_OUTPUT_FILES_py ${GEN_OUTPUT_FILE})

endmacro()

macro(_generate_module_owl ARG_PKG ARG_GEN_OUTPUT_DIR ARG_GENERATED_FILES)
  set(GEN_OUTPUT_DIR ${ARG_GEN_OUTPUT_DIR})
  file(MAKE_DIRECTORY ${GEN_OUTPUT_DIR})
  
  set(OWL_GENERATED_NAME ${ARG_PKG}.owl)
  add_custom_target(${OWL_GENERATED_NAME} ALL)
  
  add_custom_command(
    TARGET ${OWL_GENERATED_NAME}
    PRE_BUILD
    COMMAND ${CATKIN_ENV} ${PYTHON_EXECUTABLE}
        ${GENPKG_OWL_BIN}
        -p ${ARG_PKG}
        -o ${GEN_OUTPUT_DIR}
    COMMENT "Generating OWL ontologies for some package"
  )
  
endmacro()

macro(generate_pkg_owl TARGET_PKG ARG_PKG)
  set(GEN_OUTPUT_DIR "${CATKIN_DEVEL_PREFIX}/${TARGET_PKG}/${ARG_PKG}")
  set(GENERATED_FILES "-")
  _generate_module_owl(${ARG_PKG} ${GEN_OUTPUT_DIR} ${GENERATED_FILES})
endmacro()
