import { useState } from 'react';
import type { Command, EntityData } from '../types/simulation';
import styles from './BuildMode.module.css';

type ObjectKind = 'algae_reef' | 'protein_grotto' | 'decorative_rock' | 'castle';

const OBJECT_CARDS: Array<{ kind: ObjectKind; icon: string; name: string; detail: string; group: string }> = [
    { kind: 'algae_reef', icon: '🌿', name: 'Algae Reef', detail: 'Nearby fish discover algae', group: 'Nature' },
    { kind: 'decorative_rock', icon: '🪨', name: 'Quiet Rock', detail: 'A calm piece of scenery', group: 'Nature' },
    { kind: 'castle', icon: '🏰', name: 'Castle Ruin', detail: 'A weathered underwater landmark', group: 'Structures' },
    { kind: 'protein_grotto', icon: '🫧', name: 'Protein Grotto', detail: 'Stay nearby to discover protein', group: 'Feeders' },
];

interface BuildModeProps {
    entities: EntityData[];
    onCommand: (command: Command) => void;
    onDelete: (objectId: number) => void;
    selectedObjectId: number | null;
    selectedKind: ObjectKind | null;
    onSelectKind: (kind: ObjectKind | null) => void;
}

/** Renders the object-placement tray. Mount only while Build is the active
 * mode (see ModeSwitch) — this component has no toggle of its own. */
export function BuildMode({
    entities,
    onCommand,
    onDelete,
    selectedObjectId,
    selectedKind,
    onSelectKind,
}: BuildModeProps) {
    const [notice, setNotice] = useState('Choose an object, then click inside the aquarium.');
    const placeableTypes = new Set(['castle', 'algae_reef', 'protein_grotto', 'decorative_rock']);
    const selected = entities.find((entity) => entity.id === selectedObjectId);

    const handleCancel = () => {
        onSelectKind(null);
        setNotice('Placement cancelled.');
    };

    return (
        <div className={styles.tray}>
            <div className={styles.trayHeader}>
                <div>
                    <span className={styles.eyebrow}>DECORATE YOUR WORLD</span>
                    <div className={styles.instruction}>{notice}</div>
                </div>
                <button className={styles.cancel} onClick={handleCancel}>Esc</button>
            </div>
            <div className={styles.groups}>
                {['Nature', 'Structures', 'Feeders'].map((group) => (
                    <div className={styles.group} key={group}>
                        <span className={styles.groupLabel}>{group}</span>
                        <div className={styles.cards}>
                            {OBJECT_CARDS.filter((card) => card.group === group).map((card) => (
                                <button
                                    className={selectedKind === card.kind ? styles.cardSelected : styles.card}
                                    key={card.kind}
                                    onClick={() => {
                                        onSelectKind(card.kind);
                                        setNotice(`${card.name} selected — click the aquarium to place it.`);
                                    }}
                                >
                                    <span className={styles.icon}>{card.icon}</span>
                                    <span className={styles.cardName}>{card.name}</span>
                                    <span className={styles.cardDetail}>{card.detail}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
            {selected && placeableTypes.has(selected.type) && (
                <div className={styles.inspector}>
                    <span><strong>{selected.type.replaceAll('_', ' ')}</strong> · placed object #{selected.id}</span>
                    <button onClick={() => onDelete(selected.id)}>Delete</button>
                    <button onClick={() => onCommand({ command: 'move_tank_object', data: { object_id: selected.id, x: selected.x, y: selected.y } })}>Keep here</button>
                </div>
            )}
        </div>
    );
}
