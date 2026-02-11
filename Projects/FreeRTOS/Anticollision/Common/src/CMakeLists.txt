# SPDX-FileCopyrightText: Copyright (c) 2025 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

add_library(Anticollision STATIC anticollision.c)
   
target_include_directories(Anticollision PUBLIC ./ ../include)

target_link_libraries(Anticollision PUBLIC UWB qplatform)
