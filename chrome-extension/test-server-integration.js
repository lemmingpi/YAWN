/**
 * Test Script for Web Notes Server Integration
 * This script can be run in the browser console to test server sync functionality
 *
 * Usage:
 * 1. Load a webpage with the Web Notes extension
 * 2. Open browser console
 * 3. Paste this script and run it
 * 4. Check console output for test results
 */

/* global ServerAPI, getWNConfig, setWNConfig, getNotes, setNotes, addNote, updateNote, deleteNote */
/* global isServerSyncEnabled */

const ServerIntegrationTest = {
  testResults: [],
  originalConfig: null,

  /**
   * Run all server integration tests
   */
  async runAllTests() {
    console.log("🧪 Starting Web Notes Server Integration Tests...");

    try {
      // Store original config
      this.originalConfig = await getWNConfig();

      // Run tests
      await this.testConfigurationManagement();
      await this.testServerApiConnection();
      await this.testNoteCreation();
      await this.testNoteUpdate();
      await this.testNoteDeletion();
      await this.testErrorHandling();

      // Restore original config
      await this.restoreConfiguration();

      // Show results
      this.showResults();
    } catch (error) {
      console.error("❌ Test suite failed:", error);
      await this.restoreConfiguration();
    }
  },

  /**
   * Test configuration management
   */
  async testConfigurationManagement() {
    console.log("🔧 Testing configuration management...");

    try {
      // Test setting server URL
      const testConfig = {
        syncServerUrl: "http://localhost:8000/api",
        useChromeSync: false,
      };

      const setSuccess = await setWNConfig(testConfig);
      const retrievedConfig = await getWNConfig();

      this.assert(
        setSuccess && retrievedConfig.syncServerUrl === testConfig.syncServerUrl,
        "Configuration setting and retrieval",
        "Should save and retrieve server configuration"
      );

      // Test ServerAPI config loading
      if (typeof ServerAPI !== "undefined") {
        const apiConfig = await ServerAPI.getConfig();
        this.assert(
          apiConfig.serverUrl === testConfig.syncServerUrl,
          "ServerAPI configuration loading",
          "ServerAPI should load configuration correctly"
        );
      }
    } catch (error) {
      this.assert(false, "Configuration management", `Failed: ${error.message}`);
    }
  },

  /**
   * Test server API connection
   */
  async testServerApiConnection() {
    console.log("🌐 Testing server API connection...");

    try {
      if (typeof ServerAPI === "undefined") {
        this.assert(false, "ServerAPI availability", "ServerAPI not loaded");
        return;
      }

      const isEnabled = await isServerSyncEnabled();
      this.assert(isEnabled, "Server sync enabled", "Should detect enabled server sync");

      // Test page creation (this will test the full chain: site -> page)
      const testUrl = window.location.href;
      const page = await ServerAPI.getOrCreatePage(testUrl);

      this.assert(page && page.id && page.url, "Page creation/retrieval", "Should create or retrieve page from server");
    } catch (error) {
      this.assert(false, "Server API connection", `Failed: ${error.message}`);
    }
  },

  /**
   * Test note creation
   */
  async testNoteCreation() {
    console.log("📝 Testing note creation...");

    try {
      const testUrl = window.location.href;
      const testNote = {
        id: `test-note-${Date.now()}`,
        content: "Test note for server integration",
        url: testUrl,
        elementSelector: "body",
        fallbackPosition: { x: 100, y: 100 },
        offsetX: 0,
        offsetY: 0,
        backgroundColor: "light-yellow",
        isVisible: true,
        timestamp: Date.now(),
      };

      // Test local creation with server sync
      const success = await addNote(testUrl, testNote);
      this.assert(success, "Note creation", "Should create note locally and sync to server");

      // Verify note was added to local storage
      const notes = await getNotes();
      const normalizedUrl = window.location.href.split("#")[0]; // Basic normalization
      const urlNotes = notes[normalizedUrl] || [];
      const createdNote = urlNotes.find(note => note.id === testNote.id);

      this.assert(
        createdNote && createdNote.serverId,
        "Note server ID assignment",
        "Created note should have server ID assigned"
      );
    } catch (error) {
      this.assert(false, "Note creation", `Failed: ${error.message}`);
    }
  },

  /**
   * Test note update
   */
  async testNoteUpdate() {
    console.log("✏️ Testing note update...");

    try {
      const testUrl = window.location.href;
      const notes = await getNotes();
      const normalizedUrl = testUrl.split("#")[0];
      const urlNotes = notes[normalizedUrl] || [];
      const testNote = urlNotes.find(note => note.id && note.id.startsWith("test-note-"));

      if (!testNote) {
        this.assert(false, "Note update", "No test note found to update");
        return;
      }

      const updatedContent = `Updated test note content - ${Date.now()}`;
      const updateData = {
        content: updatedContent,
        lastEdited: Date.now(),
      };

      const success = await updateNote(testUrl, testNote.id, updateData);
      this.assert(success, "Note update", "Should update note locally and sync to server");

      // Verify update was applied
      const updatedNotes = await getNotes();
      const updatedUrlNotes = updatedNotes[normalizedUrl] || [];
      const updatedNote = updatedUrlNotes.find(note => note.id === testNote.id);

      this.assert(
        updatedNote && updatedNote.content === updatedContent,
        "Note update verification",
        "Updated note should have new content"
      );
    } catch (error) {
      this.assert(false, "Note update", `Failed: ${error.message}`);
    }
  },

  /**
   * Test note deletion
   */
  async testNoteDeletion() {
    console.log("🗑️ Testing note deletion...");

    try {
      const testUrl = window.location.href;
      const notes = await getNotes();
      const normalizedUrl = testUrl.split("#")[0];
      const urlNotes = notes[normalizedUrl] || [];
      const testNote = urlNotes.find(note => note.id && note.id.startsWith("test-note-"));

      if (!testNote) {
        this.assert(false, "Note deletion", "No test note found to delete");
        return;
      }

      const success = await deleteNote(testUrl, testNote.id);
      this.assert(success, "Note deletion", "Should delete note locally and from server");

      // Verify deletion
      const updatedNotes = await getNotes();
      const updatedUrlNotes = updatedNotes[normalizedUrl] || [];
      const deletedNote = updatedUrlNotes.find(note => note.id === testNote.id);

      this.assert(!deletedNote, "Note deletion verification", "Deleted note should not exist in local storage");
    } catch (error) {
      this.assert(false, "Note deletion", `Failed: ${error.message}`);
    }
  },

  /**
   * Test error handling
   */
  async testErrorHandling() {
    console.log("⚠️ Testing error handling...");

    try {
      // Test with invalid server URL
      const invalidConfig = {
        syncServerUrl: "http://invalid-server-url-that-does-not-exist.com/api",
        useChromeSync: false,
      };

      await setWNConfig(invalidConfig);

      // Clear ServerAPI cache to force reload of config
      if (typeof ServerAPI !== "undefined") {
        ServerAPI.clearConfigCache();
      }

      // Try to create a note - should fail gracefully
      const testNote = {
        id: `error-test-note-${Date.now()}`,
        content: "Error handling test note",
        url: window.location.href,
        fallbackPosition: { x: 50, y: 50 },
        isVisible: true,
        timestamp: Date.now(),
      };

      const success = await addNote(window.location.href, testNote);

      // Should succeed locally even if server fails
      this.assert(success, "Graceful degradation", "Should save locally even when server is unavailable");

      // Verify note exists locally
      const notes = await getNotes();
      const normalizedUrl = window.location.href.split("#")[0];
      const urlNotes = notes[normalizedUrl] || [];
      const createdNote = urlNotes.find(note => note.id === testNote.id);

      this.assert(
        createdNote && !createdNote.serverId,
        "Local-only save on server failure",
        "Note should exist locally without server ID when server fails"
      );

      // Clean up test note
      await deleteNote(window.location.href, testNote.id);
    } catch (error) {
      this.assert(false, "Error handling", `Failed: ${error.message}`);
    }
  },

  /**
   * Restore original configuration
   */
  async restoreConfiguration() {
    if (this.originalConfig) {
      await setWNConfig(this.originalConfig);
      if (typeof ServerAPI !== "undefined") {
        ServerAPI.clearConfigCache();
      }
    }
  },

  /**
   * Assert test condition
   */
  assert(condition, testName, description) {
    const result = {
      name: testName,
      description: description,
      passed: !!condition,
      timestamp: new Date().toISOString(),
    };

    this.testResults.push(result);

    const status = result.passed ? "✅" : "❌";
    console.log(`${status} ${testName}: ${description}`);

    return result.passed;
  },

  /**
   * Show test results summary
   */
  showResults() {
    const passed = this.testResults.filter(r => r.passed).length;
    const total = this.testResults.length;
    const failed = total - passed;

    console.log("\n📊 Test Results Summary:");
    console.log(`Total Tests: ${total}`);
    console.log(`Passed: ${passed} ✅`);
    console.log(`Failed: ${failed} ❌`);
    console.log(`Success Rate: ${Math.round((passed / total) * 100)}%`);

    if (failed > 0) {
      console.log("\nFailed Tests:");
      this.testResults.filter(r => !r.passed).forEach(r => console.log(`❌ ${r.name}: ${r.description}`));
    }

    console.log("\n🏁 Server Integration Tests Complete");

    return {
      total,
      passed,
      failed,
      successRate: (passed / total) * 100,
      results: this.testResults,
    };
  },
};

// Auto-run tests if script is executed
if (typeof window !== "undefined" && window.location) {
  console.log("🚀 Web Notes Server Integration Test Suite");
  console.log("Run ServerIntegrationTest.runAllTests() to start testing");

  // Make test suite available globally for manual execution
  window.ServerIntegrationTest = ServerIntegrationTest;
}
