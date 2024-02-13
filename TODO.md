# TODO

- [x] use repro-apk instead of aapt
- [x] podman support
- [x] update-recipes .py + .yml
- [x] switch to ruamel.yaml
- [x] finish README
- [ ] log & clone commit using ls-remote
- [ ] error if appid doesn't match APK
- [ ] split ABI support (w/ APK patterns)
- [ ] index.json
- [ ] more apps
- [ ] JSON schema + validation for recipes
- [ ] JSON schema + validation for logs
- [ ] provisioning: `build_env()` and `provision.sh` are incomplete
- [ ] provisioning: `{HOME,REPO}_DIR`, `cmake`, `extra_packages: []`
- [ ] doc/unit/regression/etc. tests
- [ ] github issues for all TODOs

# Nice to have

- [ ] rebuild when failed before comparison
- [ ] rebuild when upsteam APK or tag changes
- [ ] retry downloads
- [ ] configure timeouts
- [ ] configure paths
- [ ] more build backends (libvirt, debvm)
- [ ] more CI backends (gitlab, codeberg)
- [ ] ansible playbook for e.g. VPS
- [ ] building (random) batches (of older releases)
- [ ] scan for blobs / proprietary deps (e.g. in gradle files)
- [ ] security improvements
- [ ] provisioning: non-debian images
- [ ] get rid of "type: ignore" if possible
- [ ] automated check for latest cmdline-tools
- [ ] ability to use SDK rebuilds

# Maybe

- [ ] diff on signature copying failure?
- [ ] stream build log to stderr?
- [ ] map commit to tag(s)?
- [ ] map tag to commit(s)?
- [ ] log hashes of .sh & .py?
- [ ] use apksigner instead of shasum equality?
- [ ] sigsum?
- [ ] client support?

# CLI tool (rbtlog-check)

- [ ] matrix of repo x rebuilder
- [ ] args: repo url/name, appid, code/tag, --json
- [ ] verified, unknown (not in log), missing (not in repo), error (e.g. sha256 mismatch)
- [ ] use cache dir for repo index & rbtlog checkout
- [ ] support local log dir
- [ ] colours, checkmark etc.

# dashboard website

- [ ] matrix of repo x rebuilder
- [ ] static vs dynamic
