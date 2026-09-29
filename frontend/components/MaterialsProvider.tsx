"use client";

import { createContext, useContext, useEffect, useState } from "react";

import {
  createMaterial,
  deleteMaterial,
  listMaterials,
  renameMaterial,
  type MaterialDetail,
  type MaterialSummary,
} from "@/lib/api/client";

const byName = (a: MaterialSummary, b: MaterialSummary) => a.name.localeCompare(b.name, "ja");

/**
 * ログイン中のユーザーが登録した材料の一覧と、その登録・名前変更・削除。
 * 各操作は失敗すると Error を投げる（文言は呼び出し側が表示する）。
 */
function useMaterialsState() {
  const [materials, setMaterials] = useState<MaterialSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    // 開発時の StrictMode で 2 回走っても、片付け済みの 1 回目の結果は捨てる。
    let active = true;
    listMaterials()
      .then((list) => active && setMaterials(list))
      .catch(
        (e: unknown) =>
          active &&
          setLoadError(
            `材料の一覧を読み込めませんでした（${e instanceof Error ? e.message : String(e)}）`,
          ),
      )
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  const add = async (name: string, content: string): Promise<MaterialDetail> => {
    const saved = await createMaterial(name, content);
    setMaterials((prev) => [...prev, { id: saved.id, name: saved.name }].sort(byName));
    return saved;
  };

  const rename = async (id: string, name: string) => {
    const renamed = await renameMaterial(id, name);
    setMaterials((prev) => prev.map((m) => (m.id === id ? renamed : m)).sort(byName));
  };

  const remove = async (id: string) => {
    await deleteMaterial(id);
    setMaterials((prev) => prev.filter((m) => m.id !== id));
  };

  return { materials, loading, loadError, add, rename, remove };
}

const MaterialsContext = createContext<ReturnType<typeof useMaterialsState> | null>(null);

/** 材料ページと計算画面の材料選択で同じ一覧を使うため、レイアウトで 1 つだけ持つ。 */
export function MaterialsProvider({ children }: { children: React.ReactNode }) {
  return (
    <MaterialsContext.Provider value={useMaterialsState()}>{children}</MaterialsContext.Provider>
  );
}

export function useMaterials() {
  const value = useContext(MaterialsContext);
  if (!value) throw new Error("useMaterials は MaterialsProvider の内側で使う");
  return value;
}
