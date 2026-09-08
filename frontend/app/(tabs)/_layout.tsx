import React from "react";
import { Tabs } from "expo-router";
import { Feather } from "@expo/vector-icons";
import { Platform } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { colors } from "@/src/theme";

export default function TabsLayout() {
  const insets = useSafeAreaInsets();
  // Spazio extra sotto le icone oltre alla safe-area di sistema, così la barra
  // non finisce mai sopra la navigation bar di Android e resta comoda da toccare.
  const extra = Platform.OS === "web" ? 16 : 10;
  const padBottom = insets.bottom + extra;
  const paddingTop = 8;
  const iconLabelArea = 52; // area riservata a icona + etichetta (sempre visibili)
  const barHeight = paddingTop + iconLabelArea + padBottom;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.brandPrimary,
        tabBarInactiveTintColor: colors.onSurfaceTertiary,
        tabBarStyle: {
          backgroundColor: colors.surfaceSecondary,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          height: barHeight,
          paddingTop: paddingTop,
          paddingBottom: padBottom,
        },
        tabBarItemStyle: { paddingVertical: 2 },
        tabBarLabelStyle: { fontSize: 11, fontWeight: "700", letterSpacing: 0.3 },
      }}
    >
      <Tabs.Screen
        name="chat"
        options={{
          title: "Chat",
          tabBarIcon: ({ color, size }) => (
            <Feather name="message-circle" size={size - 2} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="clienti"
        options={{
          title: "Clienti",
          tabBarIcon: ({ color, size }) => (
            <Feather name="users" size={size - 2} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="pipeline"
        options={{
          title: "Pipeline",
          tabBarIcon: ({ color, size }) => (
            <Feather name="trello" size={size - 2} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="analytics"
        options={{
          title: "Analytics",
          tabBarIcon: ({ color, size }) => (
            <Feather name="bar-chart-2" size={size - 2} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="altro"
        options={{
          title: "Altro",
          tabBarIcon: ({ color, size }) => (
            <Feather name="grid" size={size - 2} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
