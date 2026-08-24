import { useEffect } from "react";
import { View } from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "@/src/auth";
import { Loading } from "@/src/components/ui";
import { colors } from "@/src/theme";

export default function Index() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (user) router.replace("/priorities");
    else router.replace("/login");
  }, [user, loading]);

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Loading />
    </View>
  );
}
