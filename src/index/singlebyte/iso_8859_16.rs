// AUTOGENERATED FROM index-iso-8859-16.txt, ORIGINAL COMMENT FOLLOWS:
//
// Any copyright is dedicated to the Public Domain.
// https://creativecommons.org/publicdomain/zero/1.0/
//
// For details on index index-iso-8859-16.txt see the Encoding Standard
// https://encoding.spec.whatwg.org/
//
// Identifier: 55676320d2d1b6e6909f5b3d741a7cf0cefc84e920aa4474afc091459111c2e3
// Date: 2014-09-15

static FORWARD_TABLE: &'static [u16] = &[
    128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142,
    143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157,
    158, 159, 160, 260, 261, 321, 8364, 8222, 352, 167, 353, 169, 536, 171,
    377, 173, 378, 379, 176, 177, 268, 322, 381, 8221, 182, 183, 382, 269, 537,
    187, 338, 339, 376, 380, 192, 193, 194, 258, 196, 262, 198, 199, 200, 201,
    202, 203, 204, 205, 206, 207, 272, 323, 210, 211, 212, 336, 214, 346, 368,
    217, 218, 219, 220, 280, 538, 223, 224, 225, 226, 259, 228, 263, 230, 231,
    232, 233, 234, 235, 236, 237, 238, 239, 273, 324, 242, 243, 244, 337, 246,
    347, 369, 249, 250, 251, 252, 281, 539, 255,
];

/// Returns the index code point for pointer `code` in this index.
#[inline]
#[stable]
pub fn forward(code: u8) -> u16 {
    FORWARD_TABLE[(code - 0x80) as uint]
}

static BACKWARD_TABLE_LOWER: &'static [u8] = &[
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138,
    139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153,
    154, 155, 156, 157, 158, 159, 160, 0, 0, 0, 0, 0, 0, 167, 0, 169, 0, 171,
    0, 173, 0, 0, 176, 177, 0, 0, 0, 0, 182, 183, 0, 0, 0, 187, 0, 0, 0, 0,
    192, 193, 194, 0, 196, 0, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207,
    0, 0, 210, 211, 212, 0, 214, 0, 0, 217, 218, 219, 220, 0, 0, 223, 224, 225,
    226, 0, 228, 0, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 0, 0,
    242, 243, 244, 0, 246, 0, 0, 249, 250, 251, 252, 0, 0, 255, 0, 0, 195, 227,
    161, 162, 197, 229, 0, 0, 0, 0, 178, 185, 0, 0, 208, 240, 0, 0, 0, 0, 0, 0,
    221, 253, 0, 0, 0, 0, 0, 0, 0, 163, 179, 209, 241, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 213, 245, 188, 189, 0, 0, 0, 0, 0, 0, 215, 247, 0, 0, 0, 0, 166,
    168, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 216, 248, 0, 0, 0, 0, 0, 0,
    190, 172, 174, 175, 191, 180, 184, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 170, 186, 222, 254, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 181, 165, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 164, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
];

static BACKWARD_TABLE_UPPER: &'static [u16] = &[
    0, 0, 0, 0, 32, 64, 96, 128, 160, 0, 192, 224, 0, 0, 0, 0, 256, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 288, 0, 0, 0, 0, 320,
];

/// Returns the index pointer for code point `code` in this index.
#[inline]
#[stable]
pub fn backward(code: u32) -> u8 {
    let offset = (code >> 5) as uint;
    let offset = if offset < 262 {BACKWARD_TABLE_UPPER[offset] as uint} else {0};
    BACKWARD_TABLE_LOWER[offset + ((code & 31) as uint)]
}

#[cfg(test)]
single_byte_tests!();
