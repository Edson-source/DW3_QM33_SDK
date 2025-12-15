# Install script for directory: C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/Projects/FreeRTOS/CLI/DWM3001CDK

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "C:/Program Files (x86)/DWM3001CDK-CLI-FreeRTOS")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Debug")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "TRUE")
endif()

# Set path to fallback-tool for dependency-resolution.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "C:/Program Files (x86)/GNU Arm Embedded Toolchain/10 2021.10/bin/arm-none-eabi-objdump.exe")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/arm-cortex-m4-hard_floating/uwbdriver" TYPE STATIC_LIBRARY OPTIONAL FILES "C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/libuwbdriver.a")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/arm-cortex-m4-hard_floating/uwbdriver/cmake/uwbdriver-config.cmake")
    file(DIFFERENT _cmake_export_file_changed FILES
         "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/arm-cortex-m4-hard_floating/uwbdriver/cmake/uwbdriver-config.cmake"
         "C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/CMakeFiles/Export/bc21a1fca165660f0ece2b504d6b24bf/uwbdriver-config.cmake")
    if(_cmake_export_file_changed)
      file(GLOB _cmake_old_config_files "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/arm-cortex-m4-hard_floating/uwbdriver/cmake/uwbdriver-config-*.cmake")
      if(_cmake_old_config_files)
        string(REPLACE ";" ", " _cmake_old_config_files_text "${_cmake_old_config_files}")
        message(STATUS "Old export file \"$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/arm-cortex-m4-hard_floating/uwbdriver/cmake/uwbdriver-config.cmake\" will be replaced.  Removing files [${_cmake_old_config_files_text}].")
        unset(_cmake_old_config_files_text)
        file(REMOVE ${_cmake_old_config_files})
      endif()
      unset(_cmake_old_config_files)
    endif()
    unset(_cmake_export_file_changed)
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/arm-cortex-m4-hard_floating/uwbdriver/cmake" TYPE FILE FILES "C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/CMakeFiles/Export/bc21a1fca165660f0ece2b504d6b24bf/uwbdriver-config.cmake")
  if(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Dd][Ee][Bb][Uu][Gg])$")
    file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/arm-cortex-m4-hard_floating/uwbdriver/cmake" TYPE FILE FILES "C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/CMakeFiles/Export/bc21a1fca165660f0ece2b504d6b24bf/uwbdriver-config-debug.cmake")
  endif()
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/ProjectDefinition/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/Nordic/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/FreeRTOS/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/EventManager/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/OSAL/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/DWM3001CDK/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/HAL/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/qhal/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/qplatform/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/AppConfig/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/AppCommon/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/UWB/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/reporter/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/Helpers/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/Comm/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/AppListener/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/AppFira/cmake_install.cmake")
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
if(CMAKE_INSTALL_COMPONENT)
  if(CMAKE_INSTALL_COMPONENT MATCHES "^[a-zA-Z0-9_.+-]+$")
    set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INSTALL_COMPONENT}.txt")
  else()
    string(MD5 CMAKE_INST_COMP_HASH "${CMAKE_INSTALL_COMPONENT}")
    set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INST_COMP_HASH}.txt")
    unset(CMAKE_INST_COMP_HASH)
  endif()
else()
  set(CMAKE_INSTALL_MANIFEST "install_manifest.txt")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "C:/Users/Projetos-6/Downloads/DW3_QM33_SDK_1.1.1/SDK/Firmware/DW3_QM33_SDK_1.1.1/BuildOutput/CLI/FreeRTOS/DWM3001CDK/Debug/${CMAKE_INSTALL_MANIFEST}"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
