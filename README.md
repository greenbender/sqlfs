A FUSE file system backed by an sqlite database.

At present this is about as simple an implementation as I could make, and this
was done on purpose since it gives a nice starting point from which to build a
more complete or bespoke solution.


#### Examples ####

In memory file system.

```bash
$ mkdir -p mnt
$ ./sqlfs.py mnt/
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
$ ./sqlfs.py --encrypt mnt/
$ # ...
$ fusermount -u mnt/
```

Sqlite file backed filesystem.

```bash
$ mkdir -p mnt
$ ./sqlfs.py fs.db mnt/
$ echo "Hello World!" > mnt/helloworld
$ fusermount -u mnt/
$ file fs.db
fs.db: SQLite 3.x database, last written using SQLite version 3029000
$ ls -l mnt/
total 0
$ ./sqlfs.py fs.db mnt/
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
$ ./sqlfs.py --encrypt fsenc.db mnt/
Database Password: 
$ echo "Hello World!" > mnt/helloworld
$ fusermount -u mnt/
$ file fsenc.db
fsenc.db: data
$ ls -l mnt/
total 0
$ ./sqlfs.py --encrypt fsenc.db mnt/
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


#### Dependencies ####

##### System #####

* libfuse3 - Whatever version `pyfuse3` requires.
* libsqlcipher - Latest version (only if you want encryption support)

##### Python #####

* pyfuse3
