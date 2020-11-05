from future.utils import iteritems

license_map = {
    "Apache-2.0": ["Apache License","Version 2.0"],
    "BSD-3-Clause": ["Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:","1. Redistributions","2. Redistributions","3. Neither"],
    "BSD-2-Clause": ["Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:","1. Redistributions","2. Redistributions"],
    "GPL-2.0": ["GNU GENERAL PUBLIC LICENSE","Version 2, June 1991"],
    "GPL-3.0": ["The GNU General Public License is a free, copyleft license for software and other kinds of works.","either version 3 of the License"],
    "LGPL-2.0": ["GNU LIBRARY GENERAL PUBLIC LICENSE","Version 2, June 1991"],
    "LGPL-2.1": ["GNU Lesser General Public License","Version 2.1, February 1999"],
    "LGPL-3.0": ["GNU LESSER GENERAL PUBLIC LICENSE","Version 3, 29 June 2007"],
    "MIT": ["MIT License","Copyright ",'Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:',"The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software."],
    "MPL-2.0": ["This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed with this file, You can obtain one at https://mozilla.org/MPL/2.0/"],
    "CDDL-1.0": ["COMMON DEVELOPMENT AND DISTRIBUTION LICENSE (CDDL) Version 1.0"],
    "EPL-2.0": ["Eclipse Public License - v 2.0"],
    # XXX: many, many others
    "AGPL-3.0": ['"This License" refers to version 3 of the GNU Affero General Public License.'],
}

def recognize_license(text):
    # XXX: we could do better with a translation table, but .translate is
    # different between 2/3.
    text = text.replace("\r"," ").replace("\n"," ")
    # XXX: obviously this could be faster, but unimportant now
    for (short,conditions) in iteritems(license_map):
        match = True
        for cond in conditions:
            if not cond in text:
                match = False
                break
        if match:
            return short
    return None
