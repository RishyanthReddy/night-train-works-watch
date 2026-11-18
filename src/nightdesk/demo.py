"""Public-demo allowlist with hashes and transitive input provenance. No fetches."""
import hashlib
import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field
from nightdesk.config import PUBLIC_DEMO_BUNDLE, PUBLIC_DEMO_MANIFEST
from nightdesk.intake.mapping import safe_yaml, check_input


class Asset(BaseModel):
    model_config=ConfigDict(extra='forbid', strict=True)
    path: str
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    licence: str
    kind: str = 'file'
    input_refs: list[str] = Field(default_factory=list)


class DemoManifest(BaseModel):
    model_config=ConfigDict(extra='forbid', strict=True)
    version: int
    assets: list[Asset]


class DemoRegistry:
    def __init__(self,path,bundle=None):
        self.path=Path(path).resolve();self.bundle=bundle
        if bundle:
            if bundle.nda: raise ValueError('nda_bundle_cannot_be_public_demo')
            check_input(path,bundle)
        self.manifest=DemoManifest.model_validate(safe_yaml(self.path.read_text()))
        if self.manifest.version!=1 or not self.manifest.assets: raise ValueError('demo_manifest_version_or_empty')
        self.assets={}
        for item in self.manifest.assets:
            p=(self.path.parent/item.path).resolve()
            if p in self.assets: raise ValueError('demo_duplicate_asset')
            if item.licence not in {'synthetic','CC0'}: raise ValueError('demo_restricted_or_unknown_licence')
            self.assets[p]=item
        for p in self.assets: self._verify(p,set())

    def require(self,path,licence=None):
        p=Path(path).resolve()
        if p not in self.assets: raise ValueError('demo_input_not_manifest_listed')
        item=self.assets[p]
        if licence is not None and item.licence!=licence: raise ValueError('demo_source_licence_mismatch')
        if hashlib.sha256(p.read_bytes()).hexdigest()!=item.sha256: raise ValueError('demo_asset_hash_mismatch')
        if self.bundle: check_input(p,self.bundle)
        return item

    def _verify(self,path,active):
        if path in active: raise ValueError('demo_provenance_cycle')
        item=self.require(path);active=active|{path}
        refs=[(self.path.parent/r).resolve() for r in item.input_refs]
        if item.kind=='capture_manifest':
            body=safe_yaml(path.read_text())
            refs += [(path.parent/f[k]).resolve() for f in body['files'] for k in ('path','mapping')]
        elif item.kind in {'mapping','text_mapping'}:
            from nightdesk.intake.mapping import load_mapping
            if load_mapping(path)[0].licence != item.licence: raise ValueError('demo_mapping_licence_mismatch')
        elif path.suffix.lower()=='.json':
            body=json.loads(path.read_text())
            def follow(value):
                if isinstance(value,dict):
                    if 'licence' in value and value['licence'] not in {'synthetic','CC0'}:
                        raise ValueError('demo_nested_restricted_or_unknown_licence')
                    for key,child in value.items():
                        if key in {'url_or_path','source_path'} and isinstance(child,str):
                            p=(path.parent/child).resolve() if not Path(child).is_absolute() else Path(child).resolve()
                            self.require(p,value.get('licence'));refs.append(p)
                        elif key=='input_refs' and isinstance(child,list):
                            for ref in child:
                                if isinstance(ref,str): refs.append((path.parent/ref).resolve())
                                else: follow(ref)
                        else: follow(child)
                elif isinstance(value,list):
                    for child in value: follow(child)
            follow(body)
        elif item.kind=='aliases':
            rows=safe_yaml(path.read_text())['aliases']
            if any(r.get('licence') not in {'synthetic','CC0'} or r.get('reviewed') is not True for r in rows):
                raise ValueError('demo_alias_evidence_not_public_reviewed')
        for ref in set(refs): self._verify(ref,active)

    def paths(self,kind):
        return [p for p,item in self.assets.items() if item.kind==kind]

    def check_bundle(self):
        if self.bundle is None: return
        from nightdesk.intake.mapping import captures
        from nightdesk.intake.batch import batches
        from nightdesk.audit import read_events
        for capture in captures(self.bundle):
            c=capture['capture']; item=self.require(capture['metadata']['path'],capture['metadata']['licence'])
            if item.sha256 not in c.files: raise ValueError('demo_capture_source_hash_mismatch')
            sha=capture['metadata']['mapping_sha256']
            if not any(a.sha256==sha for a in self.assets.values()): raise ValueError('demo_mapping_not_manifest_listed')
            # Follow all source references inside retained extra fields too.
            def extra_refs(value):
                if isinstance(value,dict):
                    for k,v in value.items():
                        if k in {'url_or_path','source_path'} and isinstance(v,str): self.require(v,value.get('licence'))
                        elif k=='licence' and v not in {'synthetic','CC0'}: raise ValueError('demo_nested_restricted_or_unknown_licence')
                        else: extra_refs(v)
                elif isinstance(value,list):
                    for v in value: extra_refs(v)
            for row in capture['rows']: extra_refs(row.extra)
        for batch in batches(self.bundle): self.require(batch['metadata']['path'])
        for event in read_events(self.bundle):
            if event.kind=='aliases_confirmed' and not any(a.kind=='aliases' and a.sha256==event.payload['table_id'] for a in self.assets.values()):
                raise ValueError('demo_alias_table_not_manifest_listed')


def check_demo(path,bundle=None):
    if bundle and bundle.name == PUBLIC_DEMO_BUNDLE:
        if Path(path).resolve() != PUBLIC_DEMO_MANIFEST.resolve():
            raise ValueError('demo_bundle_requires_project_manifest')
    registry=DemoRegistry(path,bundle);registry.check_bundle()
    return registry


def demo_input(bundle, path, *, kind, licence=None):
    """Require an approved asset before any application writer uses the public bundle."""
    if bundle.name != PUBLIC_DEMO_BUNDLE:
        return None
    asset = DemoRegistry(PUBLIC_DEMO_MANIFEST, bundle).require(path, licence)
    if asset.kind not in kind:
        raise ValueError('demo_asset_kind_mismatch')
    return asset
