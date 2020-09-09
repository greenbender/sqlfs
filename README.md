![build](../../workflows/build/badge.svg)

A FUSE file system backed by an sqlite database.

At present this is about as simple an implementation as I could make, and this
was done on purpose since it gives a nice starting point from which to build a
more complete or bespoke solution.


#### Dependencies ####

##### System #####

* libfuse3-dev - Whatever version `pyfuse3` requires.
* libsqlcipher0 - Latest version (only if you want encryption support)

##### Python #####

* pyfuse3


#### Installation ####

I haven't made this available on PyPi yet so you need to download or clone this
repository.

Ensure you have installed the system dependencies (see above).

NOTE: You can just run `./sqlfs` directly and not bother with install. If you
would like to do a system-wide install just run the following.

```
sudo pip install .
```

If you want to be able to use it in `/etc/fstab`.

```
sudo ln -s /usr/local/bin/sqlfs /usr/sbin/mount.fuse.sqlfs
```

Then add a line similar to one of the following (depending on your use-case) to
`/etc/fstab`.

```
:memory:        /mnt/mem    fuse.sqlfs allow_other 0 0
:memory:        /mnt/memenc fuse.sqlfs allow_other,encrypt 0 0
/tmp/fs.db      /mnt/db     fuse.sqlfs allow_other 0 0
/tmp/fsenc.db   /mnt/dbenc  fuse.sqlfs allow_other,password=thisisinsecure 0 0
/tmp/fsenc1.db  /mnt/dbenc1 fuse.sqlfs allow_other,credentials=/etc/creds.sqlfs 0 0
```


#### Options ####

See `sqlfs --help` for basic usage.

Options that can be passed in `-o` in addition to those supported by fuse are:

* `encrypt` - Turns on encryption, equivalent to `--encrypt`. This is useful
  for encrypted in-memory databases.
* `password=PWD` - Sets a password and turns on encryption.
* `credentials=FILE` - Sets the path of a file from which a password will be
  read and turns on encryption. The file should contains password and nothing
  else.


#### Examples ####

In memory file system.

```bash
$ mkdir -p mnt
$ sqlfs mnt/
$ echo "Hello World!" > mnt/helloworld
$ ls -l mnt/
total 1
-rw-r--r-- 1 user user 13 Sep  7 13:08 helloworld
$ cat mnt/helloworld 
Hello World!
$ fusermount -u mnt/
$ ls -l mnt/
total 0
```

In memory encrypted filesystem. NOTE: A randomly generated key will be used for
encryption.

```bash
$ mkdir -p mnt
$ sqlfs --encrypt mnt/
$ # ...
$ fusermount -u mnt/
```

Sqlite file backed filesystem.

```bash
$ mkdir -p mnt
$ sqlfs fs.db mnt/
$ echo "Hello World!" > mnt/helloworld
$ fusermount -u mnt/
$ file fs.db
fs.db: SQLite 3.x database, last written using SQLite version 3029000
$ ls -l mnt/
total 0
$ sqlfs fs.db mnt/
$ ls -l mnt/
total 1
-rw-r--r-- 1 user user 13 Sep  7 13:11 helloworld
$ cat mnt/helloworld
Hello World!
$ fusermount -u mnt/
```

Sqlcipher (encrypted sqlite) file backed filesystem.

```bash
$ mkdir -p mnt
$ sqlfs --encrypt fsenc.db mnt/
Database Password: 
$ echo "Hello World!" > mnt/helloworld
$ fusermount -u mnt/
$ file fsenc.db
fsenc.db: data
$ ls -l mnt/
total 0
$ sqlfs --encrypt fsenc.db mnt/
Database Password: 
$ ls -l mnt/
total 1
-rw-r--r-- 1 user user 13 Sep  7 13:14 helloworld
$ cat mnt/helloworld
Hello World!
$ fusermount -u mnt/
```


#### Improvements ####

Right now the best supported use-case is an encrypted userspace filesystem that
is *mostly* readonly (Writing is supported but not fast). To make it anything
much more than this would require some work.

##### Add support for lookup counts #####

At the moment inode deletion doesn't happen until the filesystem is unmounted.
Adding support for lookup counts would enable inodes to be deleted at the
correct moment (when there is no more references to them).

##### Add caching support #####

At the moment all write operations are commited to the database immediately,
whilst this approach is simple, it is also very slow. Caching block writes and
inode writes so that commits could be done in a more efficient manner would
speed things up significantly.

##### Abstaction #####

It would probably be useful to make INode, Link and Block classes to add a
layer of abstraction to the database. This would help to make the other
improvements a little easier to implement.


#### Encryption ####

Encryption is supported via `sqlcipher`. Since the state of the `pysqlcipher`
package is a bit of a mess at the moment `sqlcipher` support is limited to
using `LD_PRELOAD` to load `libsqlcipher.so.0` as a drop-in replacement for
`libsqlite3.so.0`. This works really nicely on systems that support
`LD_PRELOAD` but obviously not anywhere else.
