# This is a part of rust-encoding.
# Copyright (c) 2013-2015, Kang Seonghoon.
# See README.md and LICENSE.txt for details.

import urllib
import sys
import os.path
import re
import heapq
import argparse

def open_index(path, comments):
    for line in open(path):
        line = line.strip()
        if not line: continue
        if line.startswith('#'):
            comments.append('//' + line[1:])
            continue
        parts = line.split(None, 2)
        key = int(parts[0], 0)
        value = int(parts[1], 0)
        yield key, value

def read_index(opts, crate, name, comments):
    dirname = os.path.join(os.path.dirname(__file__), crate)
    path = os.path.join(dirname, 'index-%s.txt' % name)
    if os.path.isfile(path): return open_index(path, comments)

    try: os.mkdir(opts.cache_dir)
    except OSError: pass
    cached_path = os.path.join(opts.cache_dir, '%s.txt' % name)
    if not opts.flush_cache and os.path.exists(cached_path):
        print >>sys.stderr, '(cached)',
    else:
        try:
            urllib.urlretrieve('http://encoding.spec.whatwg.org/index-%s.txt' % name,
                               cached_path)
        except Exception:
            try: os.unlink(cached_path)
            except OSError: pass
            raise

    return open_index(cached_path, comments)

def mkdir_and_open(crate, name):
    dirname = os.path.join(os.path.dirname(__file__), crate)
    try:
        os.mkdir(dirname)
    except Exception:
        pass
    return open(os.path.join(dirname, '%s.rs' % name.replace('-', '_')), 'wb')

def dedent(s):
    return re.sub(r'(?m)^\s*\|?', '', s)

def write_header(f, name, comments):
    print >>f, '// AUTOGENERATED FROM index-%s.txt, ORIGINAL COMMENT FOLLOWS:' % name
    print >>f, '//'
    for line in comments:
        print >>f, line

def write_fmt(f, args, fmt_or_cond, thenfmt=None, elsefmt=None, **kwargs):
    if thenfmt is not None:
        fmt = thenfmt if fmt_or_cond else elsefmt
    else:
        fmt = fmt_or_cond
    if fmt:
        kwargs.update(args)
        f.write(dedent(fmt).format(**kwargs))

def write_comma_separated(f, prefix, l, width=80):
    buffered = ''
    for i in l:
        i = str(i)
        if len(prefix) + len(buffered) + len(i) <= width:
            buffered += i
        else:
            print >>f, prefix + buffered.rstrip()
            buffered = i
    if buffered:
        print >>f, prefix + buffered.rstrip()

def optimize_overlapping_blocks(blocks):
    # let's imagine that there are three blocks of size 8:
    #     [X,X,1,2,3,X,X,X], [4,X,X,5,X,X,X,X], [X,X,X,X,X,X,X,6]
    # concatenating them as is results in size 24. however if we are
    # allowed to overlap them, there are shorter ways:
    #     [X,X,1,2,3,X,X,X,4,X,X,5,X,X,X,X,X,X,X,6]
    #     [4,X,X,X,5,X,X,X,1,2,3,X,X,X,X,X,X,X,6] (optimal)
    # this function returns a list of indices to reordered blocks,
    # with overlapping shifts before putting them.
    # the first block gets the maximal shift to simplify things.
    # e.g. the first example would return [(0,2), (1,0), (2,4)];
    #      the second example would return [(1,0), (0,2), (2,3)].
    #
    # if we define f(x,y) to be the maximal saving when block y is
    # next to x (note that f(x,y) != f(y,x)), this reduces to
    # the longest TSP where the vertex is a block and the edge weight
    # is f(x,y). this is NP-hard as always with a cool algorithm (ugh).
    # we therefore stick to a simple greedy algorithm that
    # *always* pick the largest saving at that time.

    pregaps = []
    postgaps = []
    for idx, blk in enumerate(blocks):
        assert any(x is not None for x in blk), 'no empty block allowed'
        for i, v in enumerate(blk):
            if v is not None: pregaps.append((-i, idx)); break
        for i, v in enumerate(reversed(blk)):
            if v is not None: postgaps.append((-i, idx)); break

    heapq.heapify(pregaps)
    heapq.heapify(postgaps)

    # a simple disjoint-set data structure
    group = [(i, 0) for i in xrange(len(blocks))] # (parent, rank)
    def get_group(i):
        parent, rank = group[i]
        if parent != i:
            parent = get_group(parent)
            group[i] = parent, rank
        return parent
    def merge_groups(i, j):
        i = get_group(i)
        j = get_group(j)
        if i != j:
            iparent, irank = group[i]
            jparent, jrank = group[j]
            if irank < jrank:
                group[i] = jparent, irank
            elif irank > jrank:
                group[j] = iparent, jrank
            else:
                group[i] = iparent, irank + 1
                group[j] = iparent, jrank

    nextblk = {}
    prevblk = {}
    for i in xrange(len(blocks)-1):
        #      <-- postgap --->
        # -----================] preblk
        # postblk [============--------
        #          <- pregap ->
        postgap, preblk = heapq.heappop(postgaps)
        pregap, postblk = heapq.heappop(pregaps)

        # avoid making a cycle.
        pregroup = get_group(preblk)
        rejected = []
        while pregroup == get_group(postblk):
            rejected.append((pregap, postblk))
            pregap, postblk = heapq.heappop(pregaps)
        for item in rejected:
            heapq.heappush(pregaps, item)

        assert preblk not in nextblk
        nextblk[preblk] = postblk, min(-pregap, -postgap)
        prevblk[postblk] = preblk
        merge_groups(preblk, postblk)

    pregap, blk = pregaps[0]
    ret = [(blk, -pregap)]
    while blk in nextblk:
        blk, shift = nextblk.pop(blk)
        ret.append((blk, shift))
    assert len(ret) == len(blocks)
    return ret

def make_minimal_trie(invdata, lowerlimit):
    maxvalue = max(invdata) + 1
    best = 0xffffffff
    besttrie = None
    for triebits in xrange(21):
        blocks = []
        upperidx = []
        blockmap = {(None,) * (1<<triebits): -1}
        for i in xrange(0, maxvalue, 1<<triebits):
            blk = [invdata.get(j) for j in xrange(i, i + (1<<triebits))]
            blockidx = blockmap.get(tuple(blk))
            if blockidx is None:
                blockidx = len(blocks)
                blockmap[tuple(blk)] = blockidx
                blocks.append(blk)
            upperidx.append(blockidx)

        lower = [None] * (1<<triebits)
        uppermap = {-1: 0}
        for idx, shift in optimize_overlapping_blocks(blocks):
            blk = blocks[idx]
            assert shift == 0 or lower[-shift:] == blk[:shift]
            uppermap[idx] = len(lower) - shift
            lower += blk[shift:]
        upper = [uppermap[idx] for idx in upperidx]

        if len(lower) < lowerlimit and best > len(lower) + len(upper):
            best = len(lower) + len(upper)
            besttrie = (triebits, lower, upper)
    return besttrie

def make_minimal_search(data, invdata, premap, maxsearch):
    minkey = min(data)
    maxvalue = max(invdata) + 1
    best = 0xffffffff
    bestsearch = None
    for searchbits in xrange(21):
        lower = []
        upper = []
        for i in xrange(0, maxvalue, 1<<searchbits):
            v = sorted(premap(invdata[j]) for j in xrange(i, i+(1<<searchbits)) if j in invdata)
            if v:
                w = sorted((y - x, j) for j, (x, y) in enumerate(zip(v, v[1:])))
                count = v[-1] - v[0]
                block = [v[0], v[-1]]
                for k, j in reversed(w):
                    if count <= maxsearch: break
                    assert v[j+1] - v[j] == k
                    count -= k
                    block.append(v[j])
                    block.append(v[j+1])
                block.sort()
                assert minkey <= block[0] and block[-1] < 0x7fff
                # (s, e) when s < 0x8000 is a range [s, e)
                # (s, e) when s >= 0x8000 is a single pair s.t. invdata[e] = s & 0x7fff
                block = [(block[i] - minkey, block[i+1] - minkey + 1)
                            if block[i] < block[i+1] else
                            (0x8000 | (block[i] - minkey), data[block[i]] & 0xffff)
                         for i in xrange(0, len(block), 2)]
                assert all(block[i] != block[i+1] for i in xrange(len(block) - 1))
            else:
                block = []
            upper.append(len(lower))
            lower += block
        upper.append(len(lower))
        if best >= len(lower) + 2 * len(upper):
            best = len(lower) + 2 * len(upper)
            bestsearch = (searchbits, lower, upper)
    return bestsearch

def generate_single_byte_index(opts, crate, name):
    data = [None] * 128
    invdata = {}
    comments = []
    for key, value in read_index(opts, crate, name, comments):
        assert 0 <= key < 128 and 0 <= value < 0xffff and data[key] is None and value not in invdata
        data[key] = value
        invdata[value] = key

    # generate a trie with a minimal amount of data
    triebits, trielower, trieupper = make_minimal_trie(invdata, lowerlimit=0x10000)

    # generate a bitmap for quickly rejecting invalid chars even in the unoptimized setting
    bitlen = 0
    while 2**bitlen <= max(invdata):
        bitlen += 1
    bitmapshift = bitlen - 5
    bitmap = 0
    for value in invdata:
        bitmap |= 1 << (value >> bitmapshift)
    assert 2**16 <= bitmap < 2**32

    args = dict(
        datasz=len(data),
        maxvalue=max(invdata),
        bitmap=bitmap,
        bitmapshift=bitmapshift,
        triebits=triebits,
        triemask=(1<<triebits)-1,
        trielowersz=len(trielower),
        trieuppersz=len(trieupper),
    )
    with mkdir_and_open(crate, name) as f:
        write_header(f, name, comments)
        write_fmt(f, args, '''\
           |
           |#[allow(dead_code)] const X: u16 = 0xffff;
           |
           |const FORWARD_TABLE: &'static [u16] = &[
        ''')
        write_comma_separated(f, '    ',
            ['%s, ' % ('X' if value is None else value) for value in data])
        write_fmt(f, args, '''\
           |]; // {datasz} entries
           |
           |/// Returns the index code point for pointer `code` in this index.
           |#[inline]
           |pub fn forward(code: u8) -> u16 {{
           |    FORWARD_TABLE[(code - 0x80) as usize]
           |}}
           |
           |#[cfg(not(feature = "no-optimized-legacy-encoding"))]
           |const BACKWARD_TABLE_LOWER: &'static [u8] = &[
        ''')
        write_comma_separated(f, '    ',
            ['%d, ' % (0 if v is None else v+0x80) for v in trielower])
        write_fmt(f, args, '''\
           |]; // {trielowersz} entries
           |
           |#[cfg(not(feature = "no-optimized-legacy-encoding"))]
           |const BACKWARD_TABLE_UPPER: &'static [u16] = &[
        ''')
        write_comma_separated(f, '    ', ['%d, ' % v for v in trieupper])
        write_fmt(f, args, '''\
           |]; // {trieuppersz} entries
           |
           |/// Returns the index pointer for code point `code` in this index.
           |#[inline]
           |#[cfg(not(feature = "no-optimized-legacy-encoding"))]
           |pub fn backward(code: u32) -> u8 {{
           |    let offset = (code >> {triebits}) as usize;
           |    let offset = if offset < {trieuppersz} {{BACKWARD_TABLE_UPPER[offset] as usize}} else {{0}};
           |    BACKWARD_TABLE_LOWER[offset + ((code & {triemask}) as usize)]
           |}}
           |
           |/// Returns the index pointer for code point `code` in this index.
           |#[cfg(feature = "no-optimized-legacy-encoding")]
           |pub fn backward(code: u32) -> u8 {{
           |    if code > {maxvalue} || (({bitmap:#x}u32 >> (code >> {bitmapshift})) & 1) == 0 {{ return 0; }}
           |    let code = code as u16;
           |    for i in 0..0x80 {{
           |        if FORWARD_TABLE[i as usize] == code {{ return 0x80 + i; }}
           |    }}
           |    0
           |}}
           |
           |#[cfg(test)]
           |single_byte_tests! {{
           |}}
        ''')

    forwardsz = 2 * len(data)
    backwardsz = len(trielower) + 2 * len(trieupper)
    return forwardsz, backwardsz, 0

def generate_multi_byte_index(opts, crate, name):
    # some indices need an additional function for efficient mapping.
    premap = lambda i: i
    premapcode = ''
    if not opts.no_premapping:
        if name == 'euc-kr':
            def premap(i):
                r, c = divmod(i, 190)
                if c >= 96:
                    if r < 44: pass
                    elif r < 47: return None
                    elif r < 72: r -= 3
                    elif r < 73: return None
                    else: r -= 4
                    return r * (190 - 96) + (c - 96)
                else:
                    if c < 26: pass
                    elif c < 32: return None
                    elif c < 58: c -= 6
                    elif c < 64: return None
                    else: c -= 12
                    return (125 - 4) * (190 - 96) + r * (96 - 12) + c

            premapcode = dedent('''\
               |
               |fn premap_forward(code: u16) -> u16 {
               |    let r = code / 190;
               |    let c = code % 190;
               |    if c >= 96 {
               |        let dr = match r {
               |            0...43 => 0,
               |            44...46 => return X,
               |            47...71 => 3,
               |            72 => return X,
               |            73...124 => 4,
               |            _ => return X,
               |        };
               |        (r - dr) * (190 - 96) + (c - 96)
               |    } else {
               |        let dc = match c {
               |            0...25 => 0,
               |            26...31 => return X,
               |            32...57 => 6,
               |            58...63 => return X,
               |            _ => 12,
               |        };
               |        (125 - 4) * (190 - 96) + r * (96 - 12) + (c - dc)
               |    }
               |}
               |
               |#[cfg(feature = "no-optimized-legacy-encoding")]
               |fn premap_backward(code: u16) -> u16 {
               |    if code < (125 - 4) * (190 - 96) {
               |        let r = code / (190 - 96);
               |        let c = code % (190 - 96);
               |        let dr = match r {
               |            0...43 => 0,
               |            44...68 => 3,
               |            _ => 4,
               |        };
               |        (r + dr) * 190 + (c + 96)
               |    } else if code < X {
               |        let code = code - (125 - 4) * (190 - 96);
               |        let r = code / (96 - 12);
               |        let c = code % (96 - 12);
               |        let dc = match c {
               |            0...25 => 0,
               |            26...51 => 6,
               |            _ => 12,
               |        };
               |        r * 190 + (c + dc)
               |    } else {
               |        X
               |    }
               |}
            ''')

        elif name == 'jis0208':
            def premap(i):
                if i < 690: pass
                elif i < 1128: return None
                elif i < 1220: i -= 438
                elif i < 1410: return None
                elif i < 7808: i -= 628
                elif i < 8272: return None
                elif i < 8648: i -= 1092
                elif i < 10716: return None
                else: i -= 3160
                return i

            premapcode = dedent('''\
               |
               |fn premap_forward(code: u16) -> u16 {
               |    match code {
               |        0...689 => code,
               |        690...1127 => X,
               |        1128...1219 => code - 438,
               |        1220...1409 => X,
               |        1410...7807 => code - 628,
               |        7808...8271 => X,
               |        8272...8647 => code - 1092,
               |        8648...10715 => X,
               |        _ => code - 3160,
               |    }
               |}
               |
               |#[cfg(feature = "no-optimized-legacy-encoding")]
               |fn premap_backward(code: u16) -> u16 {
               |    match code {
               |        0...689 => code,
               |        690...781 => code + 438,
               |        782...7179 => code + 628,
               |        7180...7555 => code + 1092,
               |        _ => code.saturating_add(3160),
               |    }
               |}
            ''')

        elif name == 'jis0212':
            def premap(i):
                if i < 175: pass
                elif i < 534: return None
                elif i < 1027: i -= 359
                elif i < 1410: return None
                else: i -= 742
                return i

            premapcode = dedent('''\
               |
               |fn premap_forward(code: u16) -> u16 {
               |    match code {
               |        0...174 => code,
               |        175...533 => X,
               |        534...1026 => code - 359,
               |        1027...1409 => X,
               |        _ => code - 742,
               |    }
               |}
               |
               |#[cfg(feature = "no-optimized-legacy-encoding")]
               |fn premap_backward(code: u16) -> u16 {
               |    match code {
               |        0...174 => code,
               |        175...667 => code + 359,
               |        _ => code.saturating_add(742),
               |    }
               |}
            ''')

    data = {}        # key => value
    invdata = {}     # (the first) value => key, with some exceptions
    dups = []        # any value that is not mapped in invdata
    rawdups = []     # same to dups but a literal Rust code
    comments = []    # the comments in the index file
    morebits = False # True if the mapping needs SIP
    for key, value in read_index(opts, crate, name, comments):
        assert 0 <= key < 0xffff and 0 <= value < 0x110000 and value != 0xffff and key not in data
        if value >= 0x10000:
            assert (value >> 16) == 2
            morebits = True
        data[key] = value
        if value not in invdata:
            invdata[value] = key
        else:
            dups.append(key)

    if name == 'big5':
        # Big5 has four two-letter forward mappings, we use special entries for them
        specialidx = [1133, 1135, 1164, 1166]
        assert all(key not in data for key in specialidx)
        assert all(value not in invdata for value in xrange(len(specialidx)))
        for value, key in enumerate(specialidx):
            data[key] = value
            dups.append(key) # no consistency testing for them

        # and HKSCS additions are entirely missing from the backward mapping
        hkscslimit = (0xa1 - 0x81) * 157
        for value, key in invdata.items():
            if key < hkscslimit: del invdata[value]
        rawdups.append('0...%d' % (hkscslimit - 1)) # no consistency testing for them

        # there are also some duplicate entries where the *later* mapping is canonical
        swappedcanon = [0x2550, 0x255E, 0x2561, 0x256A, 0x5341, 0x5345]
        olddups = dups
        dups = []
        for key in olddups:
            value = data[key]
            if value in swappedcanon:
                dups.append(invdata[value])
                invdata[value] = key
            else:
                dups.append(key)

        dups = [i for i in dups if i >= hkscslimit] # cleanup

    # JIS X 0208 index has two ranges [8272,8836) and [8836,11280) to support two slightly
    # different encodings EUC-JP and Shift_JIS; the default backward function would favor
    # the former, so we need a separate mapping for the latter.
    #
    # fortunately for us, all allocated codes in [8272,8836) have counterparts in others,
    # so we only need a smaller remapping from [8272,8836) to other counterparts.
    remap = None
    if name == 'jis0208':
        REMAP_MIN = 8272
        REMAP_MAX = 8835

        invdataminusremap = {}
        for key, value in data.items():
            if value not in invdataminusremap and not REMAP_MIN <= key <= REMAP_MAX:
                invdataminusremap[value] = key

        remap = []
        for i in xrange(REMAP_MIN, REMAP_MAX+1):
            if i in data:
                assert data[i] in invdataminusremap
                value = invdataminusremap[data[i]]
                assert value < 0x10000
                remap.append(value)
            else:
                remap.append(0xffff)

    newdata = {}
    for key, value in data.items():
        key = premap(key)
        assert key is not None and 0 <= key < 0x10000 and key not in newdata
        newdata[key] = value
    data = newdata

    # generate a trie and search index with a minimal amount of data
    triebits, trielower, trieupper = make_minimal_trie(invdata, lowerlimit=0x10000)
    searchbits, searchlower, searchupper = make_minimal_search(data, invdata, premap,
            maxsearch=opts.max_backward_search_multibyte)
    # if the search degenerated to the full linear search, use a special code for them
    fulllinearsearch = (searchupper == [0, 1])

    minkey = min(data)
    maxkey = max(data) + 1
    args = dict(
        premapcode=premapcode,
        maxvalue=max(invdata),
        dataoff=minkey,
        datasz=maxkey-minkey,
        triebits=triebits,
        triemask=(1<<triebits)-1,
        trielowersz=len(trielower),
        trieuppersz=len(trieupper),
        fulllinearsearch=fulllinearsearch,
        searchbits=searchbits,
        searchmask=(1<<searchbits)-1,
        searchlowersz=len(searchlower),
        searchuppersz=len(searchupper),
        searchupperszm1=len(searchupper)-1,
    )
    if remap:
        args.update(
            remapsz=len(remap),
            remapmin=REMAP_MIN,
            remapmax=REMAP_MAX,
        )
    with mkdir_and_open(crate, name) as f:
        write_header(f, name, comments)
        write_fmt(f, args, '''\
           |
           |#[allow(dead_code)] const X: u16 = 0xffff;
           |{premapcode}
           |const FORWARD_TABLE: &'static [u16] = &[
        ''')
        write_comma_separated(f, '    ',
            ['%s, ' % (data[key] & 0xffff if key in data else 'X')
             for key in xrange(minkey, maxkey)])
        write_fmt(f, args, '''\
           |]; // {datasz} entries
        ''')
        if morebits:
            bits = []
            for i in xrange(minkey, maxkey, 32):
                v = 0
                for j in xrange(32):
                    v |= (data.get(i+j, 0) >= 0x10000) << j
                bits.append(v)
            write_fmt(f, args, '''\
               |
               |const FORWARD_TABLE_MORE: &'static [u32] = &[
            ''')
            write_comma_separated(f, '    ', ['%d, ' % v for v in bits])
            write_fmt(f, args, '''\
               |]; // {moresz} entries
            ''',
                moresz=len(bits))
        write_fmt(f, args, '''\
           |
           |/// Returns the index code point for pointer `code` in this index.
           |#[inline]
           |pub fn forward(code: u16) -> u32 {{
        ''')
        write_fmt(f, args, premapcode, '''\
           |    let code = premap_forward(code);
        ''')
        write_fmt(f, args, minkey != 0, '''\
           |    let code = (code as usize).wrapping_sub({dataoff});
        ''', '''\
           |    let code = code as usize;
        ''')
        write_fmt(f, args, '''\
           |    if code < {datasz} {{
        ''')
        write_fmt(f, args, morebits, '''\
           |        (FORWARD_TABLE[code] as u32) | (((FORWARD_TABLE_MORE[code >> 5] >> (code & 31)) & 1) << 17)
        ''', '''\
           |        FORWARD_TABLE[code] as u32
        ''')
        write_fmt(f, args, '''\
           |    }} else {{
           |        X as u32
           |    }}
           |}}
           |
           |#[cfg(not(feature = "no-optimized-legacy-encoding"))]
           |const BACKWARD_TABLE_LOWER: &'static [u16] = &[
        ''')
        write_comma_separated(f, '    ',
            ['%s, ' % ('X' if v is None else v) for v in trielower])
        write_fmt(f, args, '''\
           |]; // {trielowersz} entries
           |
           |#[cfg(not(feature = "no-optimized-legacy-encoding"))]
           |const BACKWARD_TABLE_UPPER: &'static [u16] = &[
        ''')
        write_comma_separated(f, '    ', ['%d, ' % v for v in trieupper])
        write_fmt(f, args, '''\
           |]; // {trieuppersz} entries
        ''')
        if not fulllinearsearch:
            write_fmt(f, args, '''\
               |
               |#[cfg(feature = "no-optimized-legacy-encoding")]
               |const BACKWARD_SEARCH_LOWER: &'static [(u16, u16)] = &[
            ''')
            write_comma_separated(f, '    ',
                ['(%d, %d), ' % (lo, hi) for lo, hi in searchlower])
            write_fmt(f, args, '''\
               |]; // {searchlowersz} entries
               |
               |#[cfg(feature = "no-optimized-legacy-encoding")]
               |const BACKWARD_SEARCH_UPPER: &'static [u16] = &[
            ''')
            write_comma_separated(f, '    ', ['%d, ' % v for v in searchupper])
            write_fmt(f, args, '''\
               |]; // {searchuppersz} entries
            ''')
        if remap:
            write_fmt(f, args, '''\
               |
               |const BACKWARD_TABLE_REMAPPED: &'static [u16] = &[
            ''')
            write_comma_separated(f, '    ', ['%d, ' % v for v in remap])
            write_fmt(f, args, '''\
               |]; // {remapsz} entries
            ''')
        write_fmt(f, args, '''\
           |
           |/// Returns the index pointer for code point `code` in this index.
           |#[inline]
           |#[cfg(not(feature = "no-optimized-legacy-encoding"))]
           |pub fn backward(code: u32) -> u16 {{
           |    let offset = (code >> {triebits}) as usize;
           |    let offset = if offset < {trieuppersz} {{BACKWARD_TABLE_UPPER[offset] as usize}} else {{0}};
           |    // BACKWARD_TABLE_LOWER stores the actual (pre-mapped) value
           |    // so we don't have to call premap_backward here.
           |    BACKWARD_TABLE_LOWER[offset + ((code & {triemask}) as usize)]
           |}}
           |
           |/// Returns the index pointer for code point `code` in this index.
           |#[cfg(feature = "no-optimized-legacy-encoding")]
           |pub fn backward(code: u32) -> u16 {{
           |    // avoid mistaking a placeholder for the actual value
           |    if code == X as u32 {{ return 0xffff; }}
           |    let codelo = (code & 0xffff) as u16;
        ''')
        retexpr = ('premap_backward(%s)' if premapcode else '%s') % ('(%s) + {dataoff}' if minkey != 0 else '%s')
        if morebits:
            write_fmt(f, args, '''\
               |    let codehi = code >> 16;
               |    #[inline] fn verify_and_map(codehi: u32, i: u16) -> Option<u16> {{
               |        let hi = ((FORWARD_TABLE_MORE[i as usize >> 5] >> (i & 31)) & 1) << 1;
               |        if hi != codehi {{ return None; }}
               |        Some(''' + (retexpr % 'i') + ''')
               |    }}
            ''')
            retifcorrect = 'if let Some(i_) = verify_and_map(codehi, %s) {{ return i_; }}'
        else:
            retifcorrect = 'return %s;' % (retexpr % '%s')
        write_fmt(f, args, not fulllinearsearch, '''\
           |    let offset = (code >> {searchbits}) as usize;
           |    let (start, end) = if offset < {searchupperszm1} {{
           |        (BACKWARD_SEARCH_UPPER[offset], BACKWARD_SEARCH_UPPER[offset+1])
           |    }} else {{
           |        (0, 0)
           |    }};
           |    for &(s, e) in &BACKWARD_SEARCH_LOWER[(start as usize)..(end as usize)] {{
           |        if s >= 0x8000 {{
           |            if e == codelo {{
           |                ''' + (retifcorrect % 's & 0x7fff') + '''
           |            }}
           |        }} else {{
           |            for i in s..e {{
           |                if FORWARD_TABLE[i as usize] == codelo {{
           |                    ''' + (retifcorrect % 'i') + '''
           |                }}
           |            }}
           |        }}
           |    }}
        ''', '''\
           |    if code <= {maxvalue} {{
           |        for (i, &v) in FORWARD_TABLE.iter().enumerate() {{
           |            if v == codelo {{
           |                ''' + (retifcorrect % 'i as u16') + '''
           |            }}
           |        }}
           |    }}
        ''')
        write_fmt(f, args, '''\
           |    X
           |}}
        ''')
        write_fmt(f, args, name == 'jis0208', '''\
           |
           |/// Returns the index shift_jis pointer for code point `code`.
           |#[inline]
           |pub fn backward_remapped(code: u32) -> u16 {{
           |    let value = backward(code);
           |    if {remapmin} <= value && value <= {remapmax} {{
           |        BACKWARD_TABLE_REMAPPED[(value - {remapmin}) as usize]
           |    }} else {{
           |        value
           |    }}
           |}}
        ''')
        write_fmt(f, args, '''\
           |
           |#[cfg(test)]
           |multi_byte_tests! {{
        ''')
        write_fmt(f, args, remap, '''\
           |    remap = [{remapmin}, {remapmax}],
        ''')
        if dups or rawdups:
            write_fmt(f, args, '''\
               |    dups = [
            ''')
            write_comma_separated(f, '        ', ['%s, ' % v for v in rawdups] + ['%d, ' % v for v in sorted(dups)])
            write_fmt(f, args, '''\
               |    ]
            ''')
        else:
            write_fmt(f, args, '''\
               |    dups = []
            ''')
        write_fmt(f, args, '''\
           |}}
        ''')

    forwardsz = 2 * (maxkey - minkey)
    backwardsz = 2 * len(trielower) + 2 * len(trieupper)
    backwardszslow = 2 * len(searchlower) + 4 * len(searchupper)
    backwardmore = 0
    if morebits: backwardmore += 4 * ((maxkey - minkey + 31) // 32)
    if remap: backwardmore += 2 * len(remap)
    return forwardsz, backwardsz + backwardmore, backwardszslow + backwardmore

def generate_multi_byte_range_lbound_index(opts, crate, name):
    data = []
    comments = []
    for key, value in read_index(opts, crate, name, comments):
        data.append((key, value))
    assert data and data == sorted(data)

    minkey, minvalue = data[0]
    maxkey, maxvalue = data[-1]
    if data[0] != (0, 0):
        data.insert(0, (0, 0))
    maxlog2 = 0
    while 2**(maxlog2 + 1) <= len(data):
        maxlog2 += 1

    if name == 'gb18030-ranges':
        keyubound = 0x110000
        valueubound = 126 * 10 * 126 * 10
    else:
        keyubound = maxkey + 1
        valueubound = maxvalue + 1

    args = dict(
        datasz=len(data),
        minkey=minkey,
        maxkey=maxkey,
        keyubound=keyubound,
        minvalue=minvalue,
        maxvalue=maxvalue,
        valueubound=valueubound,
    )
    with mkdir_and_open(crate, name) as f:
        write_header(f, name, comments)
        write_fmt(f, args, '''\
           |
           |const FORWARD_TABLE: &'static [u32] = &[
        ''')
        write_comma_separated(f, '    ', ['%d, ' % value for key, value in data])
        write_fmt(f, args, '''\
           |]; // {datasz} entries
           |
           |const BACKWARD_TABLE: &'static [u32] = &[
        ''')
        write_comma_separated(f, '    ', ['%d, ' % key for key, value in data])
        write_fmt(f, args, '''\
           |]; // {datasz} entries
           |
           |fn search(code: u32, fromtab: &'static [u32], totab: &'static [u32]) -> u32 {{
           |    let mut i = if code >= fromtab[{firstoff}] {{{firstdelta}}} else {{0}};
        ''',
            firstoff=2**maxlog2 - 1,
            firstdelta=len(data) - 2**maxlog2 + 1)
        for i in xrange(maxlog2-1, -1, -1):
            write_fmt(f, args, '''\
               |    if code >= fromtab[i{plusoff}] {{ i += {delta}; }}
            ''',
                plusoff='+%d' % (2**i-1) if i > 0 else '',
                delta=2**i)
        write_fmt(f, args, '''\
           |    (code - fromtab[i-1]) + totab[i-1]
           |}}
           |
           |/// Returns the index code point for pointer `code` in this index.
           |#[inline]
           |pub fn forward(code: u32) -> u32 {{
        ''')
        write_fmt(f, args, minkey > 0, '''\
           |    if code < {minkey} {{ return 0xffffffff; }}
        ''')
        # GB 18030 has "invalid" region inside and a singular mapping
        write_fmt(f, args, name == 'gb18030-ranges', '''\
           |    if (code > 39419 && code < 189000) || code > 1237575 {{ return 0xffffffff; }}
           |    if code == 7457 {{ return 0xe7c7; }}
        ''')
        write_fmt(f, args, '''\
           |    search(code, BACKWARD_TABLE, FORWARD_TABLE)
           |}}
           |
           |/// Returns the index pointer for code point `code` in this index.
           |#[inline]
           |pub fn backward(code: u32) -> u32 {{
        ''')
        write_fmt(f, args, minvalue > 0, '''\
           |    if code < {minvalue} {{ return 0xffffffff; }}
        ''')
        # GB 18030 has a singular mapping
        write_fmt(f, args, name == 'gb18030-ranges', '''\
           |    if code == 0xe7c7 {{ return 7457; }}
        ''')
        write_fmt(f, args, '''\
           |    search(code, FORWARD_TABLE, BACKWARD_TABLE)
           |}}
           |
           |#[cfg(test)]
           |multi_byte_range_tests! {{
           |    key = [{minkey}, {maxkey}], key < {keyubound},
           |    value = [{minvalue}, {maxvalue}], value < {valueubound}
           |}}
        ''')

    forwardsz = 4 * len(data)
    backwardsz = 4 * len(data)
    return forwardsz, backwardsz, backwardsz

INDICES = [
    ('singlebyte/armscii-8',       generate_single_byte_index),

    ('singlebyte/ibm866',          generate_single_byte_index),
    ('singlebyte/iso-8859-2',      generate_single_byte_index),
    ('singlebyte/iso-8859-3',      generate_single_byte_index),
    ('singlebyte/iso-8859-4',      generate_single_byte_index),
    ('singlebyte/iso-8859-5',      generate_single_byte_index),
    ('singlebyte/iso-8859-6',      generate_single_byte_index),
    ('singlebyte/iso-8859-7',      generate_single_byte_index),
    ('singlebyte/iso-8859-8',      generate_single_byte_index),
    ('singlebyte/iso-8859-10',     generate_single_byte_index),
    ('singlebyte/iso-8859-13',     generate_single_byte_index),
    ('singlebyte/iso-8859-14',     generate_single_byte_index),
    ('singlebyte/iso-8859-15',     generate_single_byte_index),
    ('singlebyte/iso-8859-16',     generate_single_byte_index),
    ('singlebyte/koi8-r',          generate_single_byte_index),
    ('singlebyte/koi8-u',          generate_single_byte_index),
    ('singlebyte/macintosh',       generate_single_byte_index),
    ('singlebyte/windows-874',     generate_single_byte_index),
    ('singlebyte/windows-1250',    generate_single_byte_index),
    ('singlebyte/windows-1251',    generate_single_byte_index),
    ('singlebyte/windows-1252',    generate_single_byte_index),
    ('singlebyte/windows-1253',    generate_single_byte_index),
    ('singlebyte/windows-1254',    generate_single_byte_index),
    ('singlebyte/windows-1255',    generate_single_byte_index),
    ('singlebyte/windows-1256',    generate_single_byte_index),
    ('singlebyte/windows-1257',    generate_single_byte_index),
    ('singlebyte/windows-1258',    generate_single_byte_index),
    ('singlebyte/x-mac-cyrillic',  generate_single_byte_index),

    ('tradchinese/big5',           generate_multi_byte_index),
    ('korean/euc-kr',              generate_multi_byte_index),
    ('simpchinese/gb18030',        generate_multi_byte_index),
    ('japanese/jis0208',           generate_multi_byte_index),
    ('japanese/jis0212',           generate_multi_byte_index),

    ('simpchinese/gb18030-ranges', generate_multi_byte_range_lbound_index),
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--flush-cache', action='store_true',
                        help='flush the download cache')
    parser.add_argument('--cache-dir',
                        default=os.path.join(os.path.dirname(sys.argv[0]), '.cache'),
                        help='set the download cache directory [default: %(default)s]')
    parser.add_argument('--singlebyte', dest='func_filter', action='store_const',
                        const=generate_single_byte_index,
                        help='generate only single-byte indices')
    parser.add_argument('--multibyte', dest='func_filter', action='store_const',
                        const=generate_multi_byte_index,
                        help='generate only multi-byte indices')
    parser.add_argument('--max-backward-search-multibyte', type=lambda v: int(v, 0),
                        metavar='MAX_SEARCH', default='0x200',
                        help='set the max search limit of the unoptimized backward mapping '
                             'for multi-byte indices [default: %(default)s]\n')
    parser.add_argument('--no-premapping', action='store_true',
                        help='disable premapping; trades table size for decoder performance')
    parser.add_argument('filters', nargs='*',
                        help='substring of indices to regenerate')
    opts = parser.parse_args()

    totalsz = totalszslow = 0
    for index, generate in INDICES:
        crate, _, index = index.partition('/')
        if opts.filters and all(s not in index for s in opts.filters): continue
        if opts.func_filter and generate is not opts.func_filter: continue
        print >>sys.stderr, 'generating index %s...' % index,
        forwardsz, backwardsz, backwardszslow = generate(opts, crate, index)
        totalsz += forwardsz + backwardsz
        totalszslow += forwardsz + backwardszslow
        print >>sys.stderr, '%d + %d (%d) = %d (%d) bytes.' % \
                (forwardsz, backwardsz, backwardszslow,
                 forwardsz + backwardsz, forwardsz + backwardszslow)
    print >>sys.stderr, 'total %d (%d) bytes.' % (totalsz, totalszslow)

if __name__ == '__main__':
    main()

