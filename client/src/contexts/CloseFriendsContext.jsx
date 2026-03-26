import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useAuth } from "./AuthContext";
import * as friendGroupsApi from "../api/friendGroups";

const CloseFriendsContext = createContext({ closeFriendIds: new Set(), isCloseFriend: () => false, refresh: () => {} });

export function CloseFriendsProvider({ children }) {
  const { user } = useAuth();
  const [ids, setIds] = useState(new Set());

  const fetch = useCallback(() => {
    if (!user) {
      setIds(new Set());
      return;
    }
    friendGroupsApi.getCloseFriends()
      .then((res) => {
        setIds(new Set((res.data?.members || []).map((m) => m.user_id)));
      })
      .catch(() => {});
  }, [user]);

  useEffect(() => { fetch(); }, [fetch]);

  const isCloseFriend = useCallback((userId) => ids.has(userId), [ids]);

  const value = useMemo(() => ({ closeFriendIds: ids, isCloseFriend, refresh: fetch }), [ids, isCloseFriend, fetch]);

  return (
    <CloseFriendsContext.Provider value={value}>
      {children}
    </CloseFriendsContext.Provider>
  );
}

export function useCloseFriends() {
  return useContext(CloseFriendsContext);
}
