### sqlfs ###

A FUSE file sytsem backed by and sqlite database.

At present it is about as simple an implementation as I could make, and this
was done on purpose since it gives a nice starting point on which to build more
complete or bespoke solution.


#### Improvements ####

1. Add support for lookup counts.

  At the moment inodes deletion doesn't happen until the filesystem is
  unmounted. Adding supprt for lookup counts would enable inodes to be deleted
  at the correct moment (when there is no references to them).

2. Add caching support.

  At the moment all write operations are commited tot the database immediately,
  whilst this approach is simple, it is also very slow. Caching block writes
  and inode writes so that commits could be done in a more efficient manner
  would speed things up significantly.

3. Abstaction.

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

System dependencies.

  * libfuse3 - Whatever version `pyfuse3` requires.
  * libsqlcipher - Latest version (only if you want encryption support)

Python depenencies.

  * pyfuse3
