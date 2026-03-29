import React from 'react';
import { StatusBar, Text } from 'react-native';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AppProvider } from './src/AppContext';
import { C } from './src/theme';

import ScannerScreen  from './src/screens/ScannerScreen';
import DetailScreen   from './src/screens/DetailScreen';
import PortfolioScreen from './src/screens/PortfolioScreen';
import NewsScreen     from './src/screens/NewsScreen';
import SettingsScreen from './src/screens/SettingsScreen';

const Tab   = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

const NAV_THEME = {
  ...DefaultTheme,
  dark: true,
  colors: {
    ...DefaultTheme.colors,
    background: C.bg,
    card:       C.surface,
    text:       C.text,
    border:     C.border,
    notification: C.blue,
  },
};

const HEADER_OPTS = {
  headerStyle:      { backgroundColor: C.surface },
  headerTintColor:  C.text,
  headerTitleStyle: { fontWeight: '700', color: C.text },
};

function ScannerStack() {
  return (
    <Stack.Navigator screenOptions={HEADER_OPTS}>
      <Stack.Screen
        name="ScannerMain"
        component={ScannerScreen}
        options={{ title: '📡 Options Scanner' }}
      />
      <Stack.Screen
        name="Detail"
        component={DetailScreen}
        options={({ route }) => ({
          title: `${route.params?.candidate?.ticker || ''} Detail`,
        })}
      />
    </Stack.Navigator>
  );
}

function PortfolioStack() {
  return (
    <Stack.Navigator screenOptions={HEADER_OPTS}>
      <Stack.Screen
        name="PortfolioMain"
        component={PortfolioScreen}
        options={{ title: '💼 Portfolio' }}
      />
    </Stack.Navigator>
  );
}

function NewsStack() {
  return (
    <Stack.Navigator screenOptions={HEADER_OPTS}>
      <Stack.Screen
        name="NewsMain"
        component={NewsScreen}
        options={{ title: '📰 Market News' }}
      />
    </Stack.Navigator>
  );
}

function SettingsStack() {
  return (
    <Stack.Navigator screenOptions={HEADER_OPTS}>
      <Stack.Screen
        name="SettingsMain"
        component={SettingsScreen}
        options={{ title: '⚙️ Settings' }}
      />
    </Stack.Navigator>
  );
}

const TabIcon = ({ label, focused }) => (
  <Text style={{ fontSize: 20 }}>
    {{ Scanner: '📡', Portfolio: '💼', News: '📰', Settings: '⚙️' }[label]}
  </Text>
);

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <AppProvider>
          <NavigationContainer theme={NAV_THEME}>
            <StatusBar barStyle="light-content" backgroundColor={C.bg} />
            <Tab.Navigator
              screenOptions={({ route }) => ({
                headerShown: false,
                tabBarStyle: {
                  backgroundColor: C.surface,
                  borderTopColor:  C.border,
                  borderTopWidth:  1,
                  height: 60,
                  paddingBottom: 8,
                  paddingTop: 4,
                },
                tabBarActiveTintColor:   C.blue,
                tabBarInactiveTintColor: C.text3,
                tabBarIcon: ({ focused }) => (
                  <TabIcon label={route.name} focused={focused} />
                ),
                tabBarLabelStyle: { fontSize: 10, fontWeight: '600' },
              })}
            >
              <Tab.Screen name="Scanner"   component={ScannerStack} />
              <Tab.Screen name="Portfolio" component={PortfolioStack} />
              <Tab.Screen name="News"      component={NewsStack} />
              <Tab.Screen name="Settings"  component={SettingsStack} />
            </Tab.Navigator>
          </NavigationContainer>
        </AppProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
