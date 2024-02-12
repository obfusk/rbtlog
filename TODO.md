# TODO

- [x] use repro-apk instead of aapt
- [x] podman support
- [x] update-recipes .py + .yml
- [x] switch to ruamel.yaml
- [ ] more apps
- [ ] finish README
- [ ] github issues for all TODOs
- [ ] JSON schema + validation for recipes
- [ ] JSON schema + validation for logs
- [ ] provisioning: `build_env()` and `provision.sh` are incomplete
- [ ] provisioning: `{HOME,REPO}_DIR` and `packages: []`

# Nice to have

- [ ] rebuild when failed before comparison
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

# Maybe

- [ ] diff on signature copying failure?
- [ ] stream build log to stderr?
- [ ] map tag to commit?
- [ ] log commit?
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
