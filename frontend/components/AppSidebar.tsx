"use client";

import { FlaskConical, LogOut, Sigma } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

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
  SidebarRail,
} from "@/components/ui/sidebar";
import { supabase } from "@/lib/supabase";

export const NAV_ITEMS = [
  { href: "/", label: "計算", icon: Sigma },
  { href: "/materials", label: "材料", icon: FlaskConical },
] as const;

/** 静的書き出しでは末尾に / が付くので、比較の前にそろえる。 */
export function normalizePath(pathname: string): string {
  return pathname.replace(/\/+$/, "") || "/";
}

export function AppSidebar() {
  const pathname = normalizePath(usePathname());
  const { session } = useAuth();

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
                <span className="grid text-left leading-tight">
                  <span className="font-semibold">Morpho</span>
                  <span className="text-xs text-muted-foreground">構造色シミュレータ</span>
                </span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
                <SidebarMenuItem key={href}>
                  <SidebarMenuButton asChild isActive={pathname === href} tooltip={label}>
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
            <SidebarMenuButton tooltip="ログアウト" onClick={() => supabase.auth.signOut()}>
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
