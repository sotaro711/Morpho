"use client";

import {
  ChevronRight,
  FlaskConical,
  History,
  LogOut,
  Sigma,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Collapsible } from "radix-ui";

import { useAuth } from "@/components/AuthProvider";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import { supabase } from "@/lib/supabase";

/** 計算ページ。構造の次元で分ける（サイドバーでは「計算」の下にまとめる）。 */
const CALC_PAGES = [
  { href: "/", label: "2次元", title: "計算 — 2次元（多層膜・段差）" },
  {
    href: "/3d",
    label: "3次元",
    title: "計算 — 3次元（球の配列・角柱の段差）",
  },
] as const;

const OTHER_PAGES = [
  { href: "/materials", label: "材料", icon: FlaskConical },
  { href: "/history", label: "履歴", icon: History },
] as const;

/** 全ページ。ヘッダのタイトル表示に使う。 */
export const NAV_ITEMS = [...CALC_PAGES, ...OTHER_PAGES] as const;

// Vercel のサイドバーに合わせ、項目を 36px の高さで少し間を空けて並べる。
const ITEM_CLASS = "h-9 gap-3 px-3";

/** 静的書き出しでは末尾に / が付くので、比較の前にそろえる。 */
export function normalizePath(pathname: string): string {
  return pathname.replace(/\/+$/, "") || "/";
}

export function AppSidebar() {
  const pathname = normalizePath(usePathname());
  const { session } = useAuth();
  const inCalc = CALC_PAGES.some((p) => p.href === pathname);

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/">
                <span className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-base">
                  🦋
                </span>
                <span className="font-semibold">Morpho</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu className="gap-0.5">
              {/* 計算: 2次元 / 3次元 を子に持つ折りたたみグループ */}
              <Collapsible.Root
                defaultOpen
                className="group/collapsible"
                asChild
              >
                <SidebarMenuItem>
                  <Collapsible.Trigger asChild>
                    <SidebarMenuButton
                      tooltip="計算"
                      isActive={inCalc}
                      className={ITEM_CLASS}
                    >
                      <Sigma />
                      <span>計算</span>
                      <ChevronRight className="ml-auto transition-transform group-data-[state=open]/collapsible:rotate-90" />
                    </SidebarMenuButton>
                  </Collapsible.Trigger>
                  <Collapsible.Content>
                    <SidebarMenuSub>
                      {CALC_PAGES.map(({ href, label }) => (
                        <SidebarMenuSubItem key={href}>
                          <SidebarMenuSubButton
                            asChild
                            isActive={pathname === href}
                          >
                            <Link href={href}>
                              <span>{label}</span>
                            </Link>
                          </SidebarMenuSubButton>
                        </SidebarMenuSubItem>
                      ))}
                    </SidebarMenuSub>
                  </Collapsible.Content>
                </SidebarMenuItem>
              </Collapsible.Root>
              {OTHER_PAGES.map(({ href, label, icon: Icon }) => (
                <SidebarMenuItem key={href}>
                  <SidebarMenuButton
                    asChild
                    isActive={pathname === href}
                    tooltip={label}
                    className={ITEM_CLASS}
                  >
                    <Link href={href}>
                      <Icon />
                      <span>{label}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <p
              className="truncate px-2 text-xs text-muted-foreground group-data-[collapsible=icon]:hidden"
              title={session?.user.email}
            >
              {session?.user.email}
            </p>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton
              tooltip="ログアウト"
              className={ITEM_CLASS}
              onClick={() => supabase.auth.signOut()}
            >
              <LogOut />
              <span>ログアウト</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
