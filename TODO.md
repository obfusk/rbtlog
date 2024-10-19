# TODO

- [x] use repro-apk instead of aapt
- [x] podman support
- [x] update-recipes .py + .yml
- [x] switch to ruamel.yaml
- [x] finish README
- [x] error if appid doesn't match APK
- [x] log & clone commit using ls-remote
- [x] split ABI support (w/ APK patterns)
- [x] index.json
- [x] JSON schema + validation for recipes
- [x] provisioning: `{HOME,REPO}_DIR`, `cmake`, `extra_packages: []`
- [x] provisioning: `build_env()` and `provision.sh` are incomplete
- [x] update modes: releases, tags, ...
- [x] JSON schema + validation for logs
- [x] about.json (name, description, link)
- [x] NB: container breakout (support libvirt?!)
- [x] spdx++
- [x] github issues for all TODOs
- [x] make & use a proper release of repro-apk binres #43
- [ ] build.py: specify commit & (no) APK for easy building/testing #471
- [ ] more apps #35
- [ ] doc/unit/regression/etc. tests #42
- [ ] `CONTRIBUTING.md`

# Nice to have

- [x] configure paths
- [x] update-recipes: support more forges (gitlab, codeberg)
- [x] update-recipes: handle errors (skip but warn)
- [x] retry downloads #46
- [ ] rebuild when failed before comparison #44
- [ ] rebuild when upsteam APK or tag changes #45
- [ ] configure timeouts #47
- [ ] more build backends (libvirt, debvm) #48
- [ ] more CI backends (gitlab, codeberg) #49
- [ ] ansible playbook for e.g. VPS #50
- [ ] building (random) batches (of older releases) #51
- [ ] build queue #52
- [ ] decentralised rebuilders: share recipes & sync workload #53
- [ ] scan for blobs / proprietary deps (e.g. in gradle files) #54
- [ ] security improvements #55
- [ ] provisioning: non-debian images #56
- [ ] get rid of "type: ignore" if possible #57
- [x] automated check for latest cmdline-tools #58 (via versions.json)
- [ ] ability to use SDK rebuilds #59
- [ ] run update-log on PRs (unless head matches create-pull-request/) #60
- [ ] git verify-commit/tag if `keys/<appid>.asc` #61
- [ ] security policy, CoC #62
- [ ] detect repo moves & log url history #63

# Maybe

- [x] rebuild when reproducibility is flaky? #64 (part of recipes now)
- [ ] diff on signature copying failure? #65
- [ ] stream build log to stderr? #66
- [ ] map commit to tag(s)? #67
- [ ] map tag to commit(s)? #68
- [ ] log hashes of .sh & .py? #69
- [x] use apksigner instead of shasum equality? #70 (rejected)
- [ ] sigsum? #71
- [ ] client support? #72

# CLI tool (rbtlog-check) #73

- [ ] matrix of repo x rebuilder
- [ ] args: repo url/name, appid, code/tag, --json
- [ ] verified, unknown (not in log), missing (not in repo), error (e.g. sha256 mismatch)
- [ ] use cache dir for repo index & rbtlog checkout
- [ ] support local log dir
- [ ] colours, checkmark etc.

# dashboard website #74

- [ ] matrix of repo x rebuilder
- [ ] static vs dynamic
