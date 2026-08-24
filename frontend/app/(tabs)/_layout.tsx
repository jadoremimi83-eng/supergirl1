import React from "react";
import { Tabs } from "expo-router";
import { Feather } from "@expo/vector-icons";
import { Platform } from "react-native";
import { colors, spacing } from "@/src/theme";

export default function TabsLayout() {
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
          height: Platform.OS === "ios" ? 88 : 68,
          paddingTop: spacing.sm,
          paddingBottom: Platform.OS === "ios" ? spacing.xl : spacing.md,
        },
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
