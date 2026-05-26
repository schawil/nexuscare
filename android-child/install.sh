#!/bin/bash
set -e

CHILD_DIR=~/nexuscare/android-child

# 1. AndroidManifest.xml
sed -i 's/com\.nexuscare\.parent/com.nexuscare.child/g' \
    "$CHILD_DIR/app/src/main/AndroidManifest.xml"

# 2. Tous les fichiers Kotlin — en-têtes de package
find "$CHILD_DIR" -name "*.kt" -exec \
    sed -i 's/com\.nexuscare\.parent/com.nexuscare.child/g' {} +

# 3. Renommer le répertoire source physiquement
SRC="$CHILD_DIR/app/src/main/java/com/nexuscare"
if [ -d "$SRC/parent" ]; then
    mv "$SRC/parent" "$SRC/child"
fi

# 4. settings.gradle.kts — nom du projet
sed -i 's/rootProject\.name = ".*"/rootProject.name = "android-child"/' \
    "$CHILD_DIR/settings.gradle.kts"

# 5. Nettoyage cache Gradle résiduel
rm -rf "$CHILD_DIR/.gradle" "$CHILD_DIR/app/build" "$CHILD_DIR/build"

echo "✅ Remplacement terminé. Vérification :"
grep -r "com.nexuscare.parent" "$CHILD_DIR" \
    --include="*.kt" --include="*.xml" --include="*.kts" \
    && echo "⚠️  Il reste des occurrences à corriger" \
    || echo "✅ Aucune occurrence résiduelle"
