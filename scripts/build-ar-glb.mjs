import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { center, prune, dedup, draco } from '@gltf-transform/functions';
import draco3d from 'draco3dgltf';

const SRC = 'assets/3d/Tombeaux_des_Askia.glb';
const DST = 'assets/3d/Tombeaux_des_Askia_ar.glb';

const io = new NodeIO()
    .registerExtensions(ALL_EXTENSIONS)
    .registerDependencies({
        'draco3d.decoder': await draco3d.createDecoderModule(),
        'draco3d.encoder': await draco3d.createEncoderModule(),
    });

const doc = await io.read(SRC);
const root = doc.getRoot();

console.log('--- Avant ---');
for (const mesh of root.listMeshes()) {
    const prims = mesh.listPrimitives();
    const mats = prims.map(p => p.getMaterial()?.getName() || '(none)').join(', ');
    console.log(`mesh: ${mesh.getName()} | materials: ${mats}`);
}

const SATELLITE_MATERIAL = 'SatMat.001';

for (const node of root.listNodes()) {
    const mesh = node.getMesh();
    if (!mesh) continue;
    const usesSat = mesh.listPrimitives().some(
        p => p.getMaterial()?.getName() === SATELLITE_MATERIAL
    );
    if (usesSat) {
        console.log(`Suppression du node "${node.getName()}" (mat ${SATELLITE_MATERIAL})`);
        node.dispose();
    }
}

await doc.transform(
    prune(),
    dedup(),
    center({ pivot: 'below' }),
);

const scene = root.getDefaultScene() || root.listScenes()[0];
let min = [Infinity, Infinity, Infinity];
let max = [-Infinity, -Infinity, -Infinity];
scene.traverse((node) => {
    const mesh = node.getMesh();
    if (!mesh) return;
    const m = node.getWorldMatrix();
    for (const prim of mesh.listPrimitives()) {
        const pos = prim.getAttribute('POSITION');
        if (!pos) continue;
        const v = [0, 0, 0];
        for (let i = 0; i < pos.getCount(); i++) {
            pos.getElement(i, v);
            const x = m[0]*v[0] + m[4]*v[1] + m[8]*v[2]  + m[12];
            const y = m[1]*v[0] + m[5]*v[1] + m[9]*v[2]  + m[13];
            const z = m[2]*v[0] + m[6]*v[1] + m[10]*v[2] + m[14];
            if (x < min[0]) min[0] = x; if (x > max[0]) max[0] = x;
            if (y < min[1]) min[1] = y; if (y > max[1]) max[1] = y;
            if (z < min[2]) min[2] = z; if (z > max[2]) max[2] = z;
        }
    }
});

const size = [max[0]-min[0], max[1]-min[1], max[2]-min[2]];
console.log(`\n--- Apres suppression + center ---`);
console.log(`bbox min: ${min.map(n => n.toFixed(2)).join(', ')}`);
console.log(`bbox max: ${max.map(n => n.toFixed(2)).join(', ')}`);
console.log(`dimensions (m): ${size.map(n => n.toFixed(2)).join(' x ')}`);

const TARGET_HEIGHT = 0.5;
const currentHeight = size[1];
const scale = TARGET_HEIGHT / currentHeight;
console.log(`echelle pour hauteur ${TARGET_HEIGHT}m: ${scale.toFixed(4)}`);

for (const node of scene.listChildren()) {
    const s = node.getScale();
    node.setScale([s[0] * scale, s[1] * scale, s[2] * scale]);
    const t = node.getTranslation();
    node.setTranslation([t[0] * scale, t[1] * scale, t[2] * scale]);
}

await doc.transform(
    draco({ method: 'edgebreaker' }),
);

await io.write(DST, doc);
console.log(`\nEcrit: ${DST}`);
