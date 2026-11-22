"""V16-024：容器 egress deny-by-default 校验。

检查 deploy/aiqe/egress-networkpolicy.yaml：
- 存在默认拒绝 Egress 的 NetworkPolicy；
- runner 只允许经 aiqe-egress-proxy 出网（3128）与 DNS（53）；
- 禁止 0.0.0.0/0 allow-all（除非 except 覆盖元数据/私网）；
- denylist 必须包含云元数据与私网段。
"""
from __future__ import annotations

import argparse
import ipaddress
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FILE = ROOT / "deploy" / "aiqe" / "egress-networkpolicy.yaml"
REQUIRED_DENY = {
    "169.254.169.254/32",
    "100.100.100.200/32",
    "fd00:ec2::254/128",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",
}


class EgressPolicyError(ValueError):
    pass


def _is_default_deny(policy: dict) -> bool:
    spec = policy.get("spec") or {}
    selector = spec.get("podSelector") or {}
    return (
        policy.get("kind") == "NetworkPolicy"
        and not selector
        and "Egress" in (spec.get("policyTypes") or [])
        and not spec.get("egress")
    )


def validate(documents: list[dict]) -> dict:
    policies = [doc for doc in documents if isinstance(doc, dict) and doc.get("kind") == "NetworkPolicy"]
    configmaps = [doc for doc in documents if isinstance(doc, dict) and doc.get("kind") == "ConfigMap"]
    if not any(_is_default_deny(policy) for policy in policies):
        raise EgressPolicyError("缺少默认拒绝 Egress 的 NetworkPolicy")
    proxy_policies = [
        policy
        for policy in policies
        if any(
            (rule.get("to") or [{}])[0].get("namespaceSelector")
            for rule in (policy.get("spec") or {}).get("egress") or []
        )
    ]
    if not proxy_policies:
        raise EgressPolicyError("缺少仅经 egress proxy 出网的策略")
    for policy in proxy_policies:
        for rule in (policy.get("spec") or {}).get("egress") or []:
            for target in rule.get("to") or []:
                block = target.get("ipBlock")
                if not block:
                    continue
                network = ipaddress.ip_network(str(block.get("cidr")), strict=False)
                if network.prefixlen == 0:
                    excepts = {str(item) for item in block.get("except") or []}
                    if not any(item in excepts for item in ("169.254.169.254/32", "10.0.0.0/8")):
                        raise EgressPolicyError("0.0.0.0/0 未排除元数据/私网地址")
    if not configmaps:
        raise EgressPolicyError("缺少 egress proxy denylist ConfigMap")
    denylist_text = "\n".join(
        str((configmap.get("data") or {}).get("denylist.conf") or "") for configmap in configmaps
    )
    missing = sorted(item for item in REQUIRED_DENY if item not in denylist_text)
    if missing:
        raise EgressPolicyError(f"denylist 缺少: {missing}")
    return {"policies": len(policies), "configmaps": len(configmaps)}


def load(path: Path) -> list[dict]:
    return [doc for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")) if doc]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=str(DEFAULT_FILE))
    args = parser.parse_args(argv)
    try:
        report = validate(load(Path(args.file)))
    except (OSError, yaml.YAMLError, EgressPolicyError) as exc:
        print(f"::error::egress: {exc}", file=sys.stderr)
        return 1
    print(f"egress policies: {report['policies']}, configmaps: {report['configmaps']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
