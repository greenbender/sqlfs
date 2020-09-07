A FUSE file sytsem backed by and sqlite database.

At present it is about as simple an implementation as I could make, and this
was done on purpose since it gives a nice starting point on which to build more
complete or bespoke solution.


#### Examples ####

In memory file system.

```
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

```
$ mkdir -p mnt
$ ./sqlfs.py --encrypt mnt/
$ # ...
$ fusermount -u mnt/
```

Sqlite file backed filesystem.

```
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

```
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

Right now the best supported use-case is as an encrypted userspace filesystem
that is *mostly* readonly (Writing is supported but not fast). To make it
anything much more than this would require some work.

##### Add support for lookup counts #####

At the moment inodes deletion doesn't happen until the filesystem is unmounted.
Adding supprt for lookup counts would enable inodes to be deleted at the
correct moment (when there is no references to them).

##### Add caching support #####

At the moment all write operations are commited tot the database immediately,
whilst this approach is simple, it is also very slow. Caching block writes and
inode writes so that commits could be done in a more efficient manner would
speed things up significantly.

##### Abstaction #####

It would probably be useful to make INode, Link and Block classes to add a
layer of abstraction to the database. It would probably also assist in making
the above improvements a little easier to implement.


#### Encryption ####

Encryption is supported via `sqlcipher`. Since the state of the `pysqlcipher`
package is a bit of a mess at the moment `sqlcipher` support is limited to
using `LD_PRELOAD` to load `libsqlcipher.so.0` in place of `libsqlite3.so.0` as
a drop-in replacement. This works really nicely on systems that support
`LD_PRELOAD` but obviously not anywhere else.


#### Dependencies ####

##### System #####

* libfuse3 - Whatever version `pyfuse3` requires.
* libsqlcipher - Latest version (only if you want encryption support)

##### Python #####

* pyfuse3
