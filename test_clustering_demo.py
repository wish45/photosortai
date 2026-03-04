#!/usr/bin/env python3
"""Demo: Test clustering algorithm without UI"""

import sys
sys.path.insert(0, '.')

import numpy as np
from pathlib import Path
from app.core.models import FaceRecord, Cluster, ScanResult
from app.core.clusterer import FaceClusterer

print("\n" + "=" * 70)
print("🧠 PhotoSorterAI 클러스터링 알고리즘 데모")
print("=" * 70)

# 시뮬레이션된 얼굴 임베딩 생성
print("\n📸 1단계: 시뮬레이션 얼굴 데이터 생성 중...")
print("-" * 70)

np.random.seed(42)
faces = []
face_count = 0

# 그룹 1: 사람 A (10개 얼굴)
print("\n👤 그룹 1: 사람 A (10개 얼굴)")
base_embedding_1 = np.array([1.0] + [0.0] * 511)
base_embedding_1 = base_embedding_1 / np.linalg.norm(base_embedding_1)

for i in range(10):
    embedding = base_embedding_1 + np.random.normal(0, 0.08, 512)
    embedding = embedding.astype(np.float32)
    embedding = embedding / np.linalg.norm(embedding)

    face = FaceRecord(
        photo_path=Path(f"/photos/group1_photo_{i}.jpg"),
        bbox=(0, 0, 100, 100),
        embedding=embedding
    )
    faces.append(face)
    face_count += 1

print(f"   ✓ 10개 얼굴 추가됨 (코사인 유사도 ~0.95)")

# 그룹 2: 사람 B (8개 얼굴)
print("\n👤 그룹 2: 사람 B (8개 얼굴)")
base_embedding_2 = np.array([0.0, 1.0] + [0.0] * 510)
base_embedding_2 = base_embedding_2 / np.linalg.norm(base_embedding_2)

for i in range(8):
    embedding = base_embedding_2 + np.random.normal(0, 0.08, 512)
    embedding = embedding.astype(np.float32)
    embedding = embedding / np.linalg.norm(embedding)

    face = FaceRecord(
        photo_path=Path(f"/photos/group2_photo_{i}.jpg"),
        bbox=(0, 0, 100, 100),
        embedding=embedding
    )
    faces.append(face)
    face_count += 1

print(f"   ✓ 8개 얼굴 추가됨 (코사인 유사도 ~0.95)")

# 그룹 3: 사람 C (6개 얼굴)
print("\n👤 그룹 3: 사람 C (6개 얼굴)")
base_embedding_3 = np.array([-1.0] + [0.0] * 511)
base_embedding_3 = base_embedding_3 / np.linalg.norm(base_embedding_3)

for i in range(6):
    embedding = base_embedding_3 + np.random.normal(0, 0.08, 512)
    embedding = embedding.astype(np.float32)
    embedding = embedding / np.linalg.norm(embedding)

    face = FaceRecord(
        photo_path=Path(f"/photos/group3_photo_{i}.jpg"),
        bbox=(0, 0, 100, 100),
        embedding=embedding
    )
    faces.append(face)
    face_count += 1

print(f"   ✓ 6개 얼굴 추가됨 (코사인 유사도 ~0.95)")

print(f"\n✅ 총 {face_count}개의 시뮬레이션 얼굴 생성 완료")

# 클러스터링 실행
print("\n" + "=" * 70)
print("🔄 2단계: UMAP + HDBSCAN 클러스터링 실행 중...")
print("-" * 70)

clusterer = FaceClusterer()

try:
    clusters = clusterer.cluster(faces)
    print(f"\n✅ 클러스터링 완료!")
    print(f"   - 클러스터 수: {len(clusters)}")

    # 결과 분석
    print("\n📊 클러스터링 결과:")
    print("-" * 70)

    for cluster in sorted(clusters, key=lambda c: len(c.face_records), reverse=True):
        print(f"\n🎯 클러스터 {cluster.cluster_id} ({cluster.size}개 얼굴)")

        # 클러스터에 속한 사진 샘플 표시
        sample_photos = [f.photo_path.name for f in cluster.face_records[:3]]
        print(f"   샘플 사진: {', '.join(sample_photos)}")
        if cluster.size > 3:
            print(f"   + {cluster.size - 3}개 더...")

        # 클러스터 검증
        first_photo = cluster.face_records[0].photo_path.name
        if "group1" in first_photo:
            status = "✓" if all("group1" in f.photo_path.name for f in cluster.face_records) else "⚠️"
        elif "group2" in first_photo:
            status = "✓" if all("group2" in f.photo_path.name for f in cluster.face_records) else "⚠️"
        elif "group3" in first_photo:
            status = "✓" if all("group3" in f.photo_path.name for f in cluster.face_records) else "⚠️"
        else:
            status = "?"

        print(f"   정확도 상태: {status}")

    # 검증 통계
    print("\n" + "=" * 70)
    print("📈 검증 통계")
    print("-" * 70)

    total_faces = sum(len(c.face_records) for c in clusters)
    print(f"\n✓ 할당된 얼굴: {total_faces}/{len(faces)}")

    if len(clusters) == 3:
        print(f"✓ 예상된 3개 클러스터 모두 생성됨")
    else:
        print(f"⚠️  예상: 3개, 실제: {len(clusters)}개 클러스터")

    # 클러스터 크기 검증
    sizes = sorted([len(c.face_records) for c in clusters], reverse=True)
    print(f"\n클러스터 크기 분포: {sizes}")
    print(f"예상: [10, 8, 6], 실제: {sizes}")

except Exception as e:
    print(f"\n❌ 클러스터링 실패: {e}")
    import traceback
    traceback.print_exc()

# ScanResult 생성
print("\n" + "=" * 70)
print("💾 3단계: ScanResult 생성")
print("-" * 70)

try:
    scan_result = ScanResult(
        input_folder=Path("/photos"),
        output_folder=Path("/output"),
        face_records=faces,
        clusters=clusters,
        total_photos=len(faces),
        photos_with_faces=len(set(f.photo_path for f in faces))
    )

    print(f"\n✅ ScanResult 생성 완료:")
    print(f"   - 입력 폴더: {scan_result.input_folder}")
    print(f"   - 출력 폴더: {scan_result.output_folder}")
    print(f"   - 스캔한 사진: {scan_result.total_photos}")
    print(f"   - 얼굴이 있는 사진: {scan_result.photos_with_faces}")
    print(f"   - 발견된 얼굴: {len(scan_result.face_records)}")
    print(f"   - 생성된 클러스터: {len(scan_result.clusters)}")

except Exception as e:
    print(f"\n❌ ScanResult 생성 실패: {e}")

print("\n" + "=" * 70)
print("✨ 데모 완료!")
print("=" * 70 + "\n")
